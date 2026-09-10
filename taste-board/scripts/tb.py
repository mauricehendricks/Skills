#!/usr/bin/env python3
"""taste-board — a local, durable library of design references.

Stdlib only (Python 3.8+). Captures are taken with headless Chrome when
available; nothing is uploaded anywhere.

Library layout (see default_root() for where it lives):

    rules.md              generic rules: a hand-written half + a derived half
    taxonomy.json         collection + tag vocabulary, with descriptions
    refs/<slug>/ref.json  one reference's metadata
    refs/<slug>/capture.png
    board.html            generated

Subcommands: add, recapture, browse, list, tag, rm, taxonomy, build
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time as _time
from pathlib import Path
from urllib.parse import urlparse

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"


def default_root():
    """Where the library lives, respecting each platform's conventions.

    macOS gets a dotfile in $HOME rather than ~/Library/Application Support:
    this is a developer tool people poke at by hand, and ~/.taste-board sits
    alongside ~/.gitconfig and ~/.ssh where they'll actually find it.
    """
    env = os.environ.get("TASTE_BOARD_HOME")
    if env:
        return Path(env).expanduser()

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser() / "taste-board"
    if IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "taste-board"
    if IS_MACOS:
        return Path.home() / ".taste-board"
    return Path.home() / ".local" / "share" / "taste-board"


def chrome_candidates():
    """Chromium-family browsers worth trying, most-likely-first, per platform."""
    if IS_MACOS:
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            "google-chrome",
            "chromium",
        ]
    if IS_WINDOWS:
        out = []
        rels = [
            r"Google\Chrome\Application\chrome.exe",
            r"Microsoft\Edge\Application\msedge.exe",
            r"Chromium\Application\chrome.exe",
            r"BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(var)
            if base:
                out.extend(str(Path(base) / rel) for rel in rels)
        out.extend(["chrome.exe", "msedge.exe", "chrome", "chromium"])
        return out
    return [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        "/usr/bin/microsoft-edge",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "brave-browser",
        "microsoft-edge",
    ]


# ---------------------------------------------------------------- utilities


def now_iso() -> str:
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (s[:maxlen].strip("-")) or "ref"


def split_list(value):
    """Accept 'a,b' or ['a','b'] or None -> clean list of strings."""
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(",")
    out = []
    for item in value:
        for part in str(item).split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def find_chrome():
    for cand in chrome_candidates():
        if os.sep in cand or "/" in cand:
            if Path(cand).exists():
                return cand
        else:
            found = shutil.which(cand)
            if found:
                return found
    return None


def no_chrome_message() -> str:
    """The 'no browser' error, carrying the fix for this platform.

    Better here than in a separate check command: it arrives at the moment it
    matters, without anyone having to know a diagnostic exists.
    """
    if IS_MACOS:
        fix = "brew install --cask google-chrome"
    elif IS_WINDOWS:
        fix = "install Chrome from https://google.com/chrome"
    else:
        fix = "sudo apt install chromium-browser  (or: sudo snap install chromium)"
    return ("no Chrome/Chromium found — %s, or skip capture and pass "
            "--image / --clipboard instead" % fix)


def human_size(n) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return "%.0f %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%d B" % n


def esc(text) -> str:
    return (
        str(text if text is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ------------------------------------------------------------------ library


class Library:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser()
        self.refs_dir = self.root / "refs"

    def ensure(self):
        self.refs_dir.mkdir(parents=True, exist_ok=True)
        rules = self.root / "rules.md"
        if not rules.exists():
            rules.write_text(RULES_SEED, encoding="utf-8")
        tax = self.root / "taxonomy.json"
        if not tax.exists():
            tax.write_text(
                json.dumps({"collections": {}, "tags": {}}, indent=2) + "\n",
                encoding="utf-8",
            )

    # -- taxonomy

    def load_taxonomy(self) -> dict:
        path = self.root / "taxonomy.json"
        if not path.exists():
            return {"collections": {}, "tags": {}}
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("collections", {})
        data.setdefault("tags", {})
        return data

    def save_taxonomy(self, data: dict):
        (self.root / "taxonomy.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    # -- refs

    def load_refs(self):
        refs = []
        if not self.refs_dir.exists():
            return refs
        for meta in sorted(self.refs_dir.glob("*/ref.json")):
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
            except (ValueError, OSError) as exc:
                print("warn: skipping %s (%s)" % (meta, exc), file=sys.stderr)
                continue
            data["_dir"] = meta.parent
            data.setdefault("slug", meta.parent.name)
            refs.append(data)
        refs.sort(key=lambda r: r.get("captured_at", ""), reverse=True)
        return refs

    def unique_slug(self, base: str) -> str:
        slug = slugify(base)
        candidate, n = slug, 2
        while (self.refs_dir / candidate).exists():
            candidate = "%s-%d" % (slug, n)
            n += 1
        return candidate

    def get(self, slug: str):
        path = self.refs_dir / slug / "ref.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_dir"] = path.parent
        data.setdefault("slug", slug)
        return data

    def save(self, ref: dict):
        d = dict(ref)
        d.pop("_dir", None)
        out = self.refs_dir / ref["slug"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "ref.json").write_text(
            json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


DERIVED_START = "<!-- taste-board:derived:start -->"
DERIVED_END = "<!-- taste-board:derived:end -->"

RULES_SEED = """# House rules

Generic, cross-project design rules. Two halves, and they behave differently.

## Yours

Hand-written. Nothing regenerates this section, and it outranks the derived half
whenever the two disagree.

### Always

-

### Never

-

## Derived

Synthesized from the reference library and regenerated as it grows — everything
between the markers is rewritten wholesale, so edit the section above instead.

{start}

_Nothing derived yet. Add references, then ask for the rules to be regenerated._

{end}
""".format(start=DERIVED_START, end=DERIVED_END)


def split_rules(text):
    """Return (before, derived, after) around the generated region.

    Missing markers yield an empty derived block and everything in `before`, so
    callers can append the region to a hand-written file without losing content.
    """
    start = text.find(DERIVED_START)
    end = text.find(DERIVED_END)
    if start == -1 or end == -1 or end < start:
        return text, "", ""
    return (
        text[:start + len(DERIVED_START)],
        text[start + len(DERIVED_START):end],
        text[end:],
    )


# ---------------------------------------------------------------- clipboard


def clipboard_png(dest):
    """Save the clipboard's image to `dest`. Returns (ok, message).

    An image pasted into a chat has no path on disk, but it is almost always
    still sitting on the system clipboard — which is the only way to get those
    bytes into the library without asking the user to save a file by hand.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if IS_MACOS:
        proc = subprocess.run(
            ["osascript", "-e", "the clipboard as «class PNGf»"],
            capture_output=True, text=True,
        )
        match = re.search(r"«data PNGf([0-9A-Fa-f]+)»", proc.stdout or "")
        if not match:
            return False, "no image on the clipboard"
        try:
            dest.write_bytes(binascii.unhexlify(match.group(1)))
        except (binascii.Error, ValueError) as exc:
            return False, "clipboard image was malformed: %s" % exc
        return True, "saved clipboard image (%s)" % human_size(dest.stat().st_size)

    if IS_WINDOWS:
        script = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
            "$i=[System.Windows.Forms.Clipboard]::GetImage();"
            "if($i -eq $null){exit 1};"
            "$i.Save('%s',[System.Drawing.Imaging.ImageFormat]::Png)" % dest
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", script],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not dest.exists():
            return False, "no image on the clipboard"
        return True, "saved clipboard image (%s)" % human_size(dest.stat().st_size)

    # Linux/BSD — Wayland first, then X11.
    for cmd in (
        ["wl-paste", "--type", "image/png"],
        ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
    ):
        if not shutil.which(cmd[0]):
            continue
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode == 0 and proc.stdout[:8] == b"\x89PNG\r\n\x1a\n":
            dest.write_bytes(proc.stdout)
            return True, "saved clipboard image (%s)" % human_size(dest.stat().st_size)
    if not shutil.which("wl-paste") and not shutil.which("xclip"):
        return False, ("no clipboard tool — sudo apt install wl-clipboard (Wayland) "
                       "or xclip (X11); --image still works without it")
    return False, "no image on the clipboard"


# ------------------------------------------------------------------ capture

# Consent dialogs are the single biggest cause of a useless capture: the page
# renders fine, but the screenshot is of a cookie banner. Hiding the usual
# suspects up front is far more reliable than trying to click "accept".
CONSENT_CSS = """
#onetrust-consent-sdk, #onetrust-banner-sdk, .onetrust-pc-dark-filter,
#CybotCookiebotDialog, #CybotCookiebotDialogBodyUnderlay, #cookiescript_injected,
#usercentrics-root, .osano-cm-window, .osano-cm-dialog, #hs-eu-cookie-confirmation,
.cc-window, .cookie-banner, .cookie-consent, .cookie-notice, #cookie-banner,
#cookie-law-info-bar, #gdpr-consent-tool-wrapper, .truste_overlay, .truste_box_overlay,
[class*="CookieConsent"], [class*="cookie-banner"], [id*="cookie-consent"],
[aria-label*="cookie" i], [aria-describedby*="cookie" i],
[class*="newsletter-modal"], [class*="NewsletterModal"], [data-testid*="cookie" i]
{ display: none !important; visibility: hidden !important; }
html, body { overflow: auto !important; position: static !important; }
body { padding-right: 0 !important; }
"""


def capture_playwright(url, dest, viewport, full_page, wait, timeout):
    """Better tier: real waits, consent suppression, true full-page.

    Returns (ok, message) or None when Playwright isn't installed, so the
    caller can fall through to Chrome.
    """
    try:
        from playwright.sync_api import Error as PWError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    w, h = (viewport.replace("x", ",").split(",") + ["900"])[:2]
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(
                viewport={"width": int(w), "height": int(h)},
                device_scale_factor=2,
            )
            try:
                try:
                    page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
                except PWError:
                    # networkidle never settles on sites with polling/analytics.
                    page.goto(url, wait_until="load", timeout=timeout * 1000)
                page.add_style_tag(content=CONSENT_CSS)
                page.wait_for_timeout(max(wait, 1) * 1000)
                page.screenshot(path=str(dest), full_page=full_page)
            finally:
                browser.close()
        if dest.exists() and dest.stat().st_size > 1000:
            return True, "captured %s (playwright)" % dest.name
        return False, "playwright produced no image"
    except Exception as exc:  # noqa: BLE001 - any engine failure should fall back
        return False, "playwright capture failed: %s" % exc


def seed_profile(temp_profile, persistent):
    """Carry cookies from the persistent profile into a throwaway one.

    Captures run in temp profiles so several can go at once (Chrome locks a
    profile directory). Copying just the cookie jar means consent choices and
    logins made during `browse` still apply, without the lock contention.
    """
    persistent = Path(persistent)
    if not persistent.exists():
        return
    for rel in ("Default/Cookies", "Default/Network/Cookies", "Local State"):
        src = persistent / rel
        if src.exists():
            dst = Path(temp_profile) / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(src, dst)
            except OSError:
                pass


def capture_chrome(url, dest, viewport="1440,900", full_page=False, wait=2,
                   timeout=45, persistent=None):
    """Zero-install tier: headless Chrome. Returns (ok, message).

    Chrome writes the PNG and then keeps running instead of exiting, so waiting
    on the process would hang. Poll for the file, wait for its size to settle
    (the write is not atomic), then terminate.
    """
    chrome = find_chrome()
    if not chrome:
        return False, no_chrome_message()

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    profile = tempfile.mkdtemp(prefix="tb-chrome-")
    if persistent:
        seed_profile(profile, persistent)
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--force-color-profile=srgb",
        "--user-data-dir=%s" % profile,
        "--window-size=%s" % viewport.replace("x", ","),
        "--virtual-time-budget=%d" % (max(wait, 1) * 1000),
        "--screenshot=%s" % dest,
    ]
    if full_page:
        cmd.append("--full-page-screenshot")
    cmd.append(url)

    proc = None
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        deadline = _time.time() + timeout
        stable, last = 0, -1
        while _time.time() < deadline:
            _time.sleep(0.5)
            size = dest.stat().st_size if dest.exists() else 0
            if size > 1000 and size == last:
                stable += 1
                if stable >= 2:  # unchanged across ~1s — write finished
                    return True, "captured %s" % dest.name
            else:
                stable = 0
            last = size
            if proc.poll() is not None and size > 1000:
                return True, "captured %s" % dest.name
            if proc.poll() is not None and size == 0:
                break
        if dest.exists() and dest.stat().st_size > 1000:
            return True, "captured %s" % dest.name
        return False, "chrome produced no image (page may need auth, or blocked the load)"
    except OSError as exc:
        return False, "capture failed: %s" % exc
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


PLAYWRIGHT_HINT = (
    "install Playwright for tougher pages: "
    "pip3 install playwright && python3 -m playwright install chromium"
)


def capture_url(url, dest, viewport="1440,900", full_page=False, wait=2,
                timeout=45, engine="auto", persistent=None):
    """Capture `url`, preferring the best engine available.

    Playwright handles slow hydration and true full-page shots; Chrome needs no
    install. A hard failure here usually means a bot check or a consent wall —
    the caller should hand that to the human rather than filing a blank card.
    """
    attempts = []

    if engine in ("auto", "playwright"):
        result = capture_playwright(url, dest, viewport, full_page, wait, timeout)
        if result is None:
            if engine == "playwright":
                return False, "playwright not installed — %s" % PLAYWRIGHT_HINT
            attempts.append("playwright not installed")
        elif result[0]:
            return result
        else:
            attempts.append(result[1])

    if engine in ("auto", "chrome"):
        ok, msg = capture_chrome(url, dest, viewport, full_page, wait, timeout,
                                 persistent=persistent)
        if ok:
            return True, msg
        attempts.append(msg)

    detail = "; ".join(attempts) or "no capture engine available"
    return False, "BLOCKED: %s" % detail


def cmd_browse(args):
    """Open a URL in a visible, persistent Chrome profile.

    This is the escape hatch for consent walls and bot checks: the human clears
    it once by hand, the cookies stick to this profile, and later headless
    captures inherit them.
    """
    chrome = find_chrome()
    if not chrome:
        print("error: %s" % no_chrome_message(), file=sys.stderr)
        return 2
    lib = Library(args.root)
    lib.ensure()
    profile = lib.root / ".chrome-profile"
    profile.mkdir(parents=True, exist_ok=True)

    print("Opening %s in a visible Chrome window.\n" % args.url)
    print("  Accept the cookie banner / clear the bot check, then close the window.")
    print("  That approval is saved to this profile, so the capture will work next.\n")
    proc = subprocess.Popen(
        [
            chrome,
            "--user-data-dir=%s" % profile,
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            args.url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        proc.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print("(still open after %ss — leaving it running)" % args.timeout)
        return 0
    print("Window closed. Re-run the capture now:")
    print("  python3 %s recapture <slug>" % Path(__file__).name)
    return 0


# -------------------------------------------------------------- subcommands


def cmd_add(args):
    lib = Library(args.root)
    lib.ensure()

    if not args.url and not args.image and not args.clipboard:
        print("error: pass --url, --image, or --clipboard", file=sys.stderr)
        return 2

    title = args.title
    if not title:
        if args.url:
            host = urlparse(args.url).netloc.replace("www.", "")
            title = host or args.url
        elif args.image:
            title = Path(args.image).stem.replace("-", " ").replace("_", " ").title()
        else:
            title = "Pasted %s" % _dt.datetime.now().strftime("%b %d %H:%M")

    slug = args.slug or lib.unique_slug(args.slug or title)
    if lib.get(slug) and not args.force:
        print("error: %s already exists (use --force to overwrite)" % slug, file=sys.stderr)
        return 2

    ref_dir = lib.refs_dir / slug
    ref_dir.mkdir(parents=True, exist_ok=True)
    capture_name = None
    notes = []

    if args.clipboard:
        ok, msg = clipboard_png(ref_dir / "capture.png")
        if not ok:
            shutil.rmtree(ref_dir, ignore_errors=True)
            print("error: %s" % msg, file=sys.stderr)
            return 2
        capture_name = "capture.png"
        print(msg, file=sys.stderr)
    elif args.image:
        src = Path(args.image).expanduser()
        if not src.exists():
            shutil.rmtree(ref_dir, ignore_errors=True)
            print("error: no such image: %s" % src, file=sys.stderr)
            return 2
        capture_name = "capture%s" % (src.suffix.lower() or ".png")
        shutil.copyfile(src, ref_dir / capture_name)
    elif args.url and not args.no_capture:
        ok, msg = capture_url(
            args.url,
            ref_dir / "capture.png",
            viewport=args.viewport,
            full_page=args.full_page,
            wait=args.wait,
            engine=args.engine,
            persistent=lib.root / ".chrome-profile",
        )
        if ok:
            capture_name = "capture.png"
        else:
            notes.append(msg)
            print("warn: %s" % msg, file=sys.stderr)

    ref = {
        "slug": slug,
        "title": title,
        "url": args.url or "",
        "collection": args.collection or "unsorted",
        "tags": split_list(args.tags),
        "why": args.why or "",
        "capture": capture_name,
        "captured_at": now_iso(),
    }
    if notes:
        ref["capture_error"] = notes[0]
    lib.save(ref)

    tax = lib.load_taxonomy()
    tax["collections"].setdefault(ref["collection"], "")
    for tag in ref["tags"]:
        tax["tags"].setdefault(tag, "")
    lib.save_taxonomy(tax)

    print(json.dumps({"slug": slug, "dir": str(ref_dir), "capture": capture_name}, indent=2))
    return 0


def cmd_recapture(args):
    """Re-shoot a reference — for when the first capture caught a consent wall."""
    lib = Library(args.root)
    ref = lib.get(args.slug)
    if not ref:
        print("error: no such reference: %s" % args.slug, file=sys.stderr)
        return 2
    if not ref.get("url"):
        print("error: %s has no URL to recapture" % args.slug, file=sys.stderr)
        return 2
    ok, msg = capture_url(
        ref["url"],
        Path(ref["_dir"]) / "capture.png",
        viewport=args.viewport,
        full_page=args.full_page,
        wait=args.wait,
        engine=args.engine,
        persistent=lib.root / ".chrome-profile",
    )
    ref["captured_at"] = now_iso()
    if ok:
        ref["capture"] = "capture.png"
        ref.pop("capture_error", None)
    else:
        ref["capture_error"] = msg
    lib.save(ref)
    print(msg)
    return 0 if ok else 1


def cmd_rules(args):
    """Show the rules file and whether its derived half has gone stale.

    The script can't synthesize rules — that needs looking at the captures — so
    its job is to report drift and record when a regeneration happened.
    """
    lib = Library(args.root)
    lib.ensure()
    path = lib.root / "rules.md"
    text = path.read_text(encoding="utf-8")
    tax = lib.load_taxonomy()
    refs = lib.load_refs()

    derived_at = tax.get("rules_derived_at")
    derived_count = tax.get("rules_derived_count", 0)
    new_refs = [r for r in refs if not derived_at or r.get("captured_at", "") > derived_at]

    if args.set_derived:
        # Splice on the markers rather than having the caller hand-edit around
        # them: a regeneration that clobbers a marker breaks every future one.
        new = sys.stdin.read().strip()
        before, _, after = split_rules(text)
        if not after:
            print(
                "error: %s has no derived markers — restore %s / %s first"
                % (path, DERIVED_START, DERIVED_END),
                file=sys.stderr,
            )
            return 2
        path.write_text("%s\n\n%s\n\n%s" % (before, new, after), encoding="utf-8")
        tax["rules_derived_at"] = now_iso()
        tax["rules_derived_count"] = len(refs)
        lib.save_taxonomy(tax)
        print("wrote derived rules and marked %d references as of %s"
              % (len(refs), tax["rules_derived_at"]))
        return 0

    if args.mark_derived:
        tax["rules_derived_at"] = now_iso()
        tax["rules_derived_count"] = len(refs)
        lib.save_taxonomy(tax)
        print("marked derived: %d references as of %s" % (len(refs), tax["rules_derived_at"]))
        return 0

    if args.show:
        print(text)
        print("---")

    print("rules file      : %s" % path)
    print("references      : %d" % len(refs))
    if not derived_at:
        print("derived         : never")
    else:
        print("derived         : %s (%d refs)" % (derived_at, derived_count))
    print("added since     : %d" % len(new_refs))
    for r in new_refs[:10]:
        print("                  %s (%s)" % (r["slug"], r.get("collection", "")))
    if len(new_refs) > 10:
        print("                  ... and %d more" % (len(new_refs) - 10))

    stale = len(new_refs) >= args.threshold or (refs and not derived_at)
    print("status          : %s" % ("STALE — worth regenerating" if stale else "current"))
    return 0


def _matches(ref, collection, tags, query):
    if collection and ref.get("collection") != collection:
        return False
    if tags and not set(t.lower() for t in tags) <= set(
        t.lower() for t in ref.get("tags", [])
    ):
        return False
    if query:
        hay = " ".join(
            [ref.get("title", ""), ref.get("url", ""), ref.get("why", "")]
            + ref.get("tags", [])
            + [ref.get("collection", "")]
        ).lower()
        if query.lower() not in hay:
            return False
    return True


def cmd_list(args):
    lib = Library(args.root)
    refs = [
        r
        for r in lib.load_refs()
        if _matches(r, args.collection, split_list(args.tags), args.query)
    ]
    if args.json:
        for r in refs:
            r.pop("_dir", None)
        print(json.dumps(refs, indent=2, ensure_ascii=False))
        return 0
    if not refs:
        print("no references matched")
        return 0
    for r in refs:
        print(
            "%-34s %-22s %s"
            % (
                r["slug"][:34],
                (r.get("collection") or "")[:22],
                ", ".join(r.get("tags", [])),
            )
        )
    print("\n%d reference(s)" % len(refs))
    return 0


def cmd_tag(args):
    lib = Library(args.root)
    ref = lib.get(args.slug)
    if not ref:
        print("error: no such reference: %s" % args.slug, file=sys.stderr)
        return 2
    tags = list(ref.get("tags", []))
    for t in split_list(args.remove):
        tags = [x for x in tags if x.lower() != t.lower()]
    for t in split_list(args.add):
        if t.lower() not in [x.lower() for x in tags]:
            tags.append(t)
    ref["tags"] = tags
    if args.collection:
        ref["collection"] = args.collection
    if args.why:
        ref["why"] = args.why
    if args.title:
        ref["title"] = args.title
    lib.save(ref)

    tax = lib.load_taxonomy()
    tax["collections"].setdefault(ref["collection"], "")
    for t in tags:
        tax["tags"].setdefault(t, "")
    lib.save_taxonomy(tax)
    print(json.dumps({"slug": ref["slug"], "collection": ref["collection"], "tags": tags}, indent=2))
    return 0


def cmd_rm(args):
    lib = Library(args.root)
    ref = lib.get(args.slug)
    if not ref:
        print("error: no such reference: %s" % args.slug, file=sys.stderr)
        return 2
    shutil.rmtree(ref["_dir"])
    print("removed %s" % args.slug)
    return 0


def cmd_taxonomy(args):
    lib = Library(args.root)
    lib.ensure()
    tax = lib.load_taxonomy()
    if args.describe:
        kind, _, rest = args.describe.partition(":")
        name, _, desc = rest.partition("=")
        bucket = "collections" if kind.startswith("c") else "tags"
        tax[bucket][name.strip()] = desc.strip()
        lib.save_taxonomy(tax)
    counts = {}
    for r in lib.load_refs():
        counts[r.get("collection", "unsorted")] = counts.get(r.get("collection", "unsorted"), 0) + 1
    if args.json:
        print(json.dumps(
            {"library": str(lib.root), "taxonomy": tax, "counts": counts},
            indent=2, ensure_ascii=False))
        return 0
    # The library path is platform-dependent, so print it rather than let
    # anyone guess: this is the command that answers "where does my stuff live".
    print("library: %s  (%d references)\n" % (lib.root, sum(counts.values())))
    print("collections:")
    for name, desc in sorted(tax["collections"].items()):
        print("  %-28s %3d  %s" % (name, counts.get(name, 0), desc))
    print("\ntags:")
    for name, desc in sorted(tax["tags"].items()):
        print("  %-28s      %s" % (name, desc))
    return 0


# -------------------------------------------------------------------- build


def _img_src(ref, out_dir: Path, embed: bool):
    cap = ref.get("capture")
    if not cap:
        return None
    path = Path(ref["_dir"]) / cap
    if not path.exists():
        return None
    if embed:
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return "data:%s;base64,%s" % (mime, data)
    try:
        # HTML always wants forward slashes; os.sep is "\" on Windows.
        return os.path.relpath(path, out_dir).replace(os.sep, "/")
    except ValueError:
        # Different drives on Windows — no relative path exists.
        return path.as_uri()


def _rules_html(root: Path):
    """Render rules.md's Always/Never bullets as a two-column panel."""
    path = root / "rules.md"
    if not path.exists():
        return ""
    section, buckets = None, {"always": [], "never": []}
    for line in path.read_text(encoding="utf-8").splitlines():
        low = line.strip().lower()
        if low.startswith("#"):
            if "always" in low:
                section = "always"
            elif "never" in low:
                section = "never"
            else:
                section = None
            continue
        if section and line.strip().startswith(("-", "*")):
            item = line.strip()[1:].strip()
            if item:
                buckets[section].append(item)
    if not buckets["always"] and not buckets["never"]:
        return ""

    def col(label, items, cls):
        lis = "".join("<li>%s</li>" % esc(i) for i in items) or "<li class=empty>—</li>"
        return '<div class="rulecol %s"><h3>%s</h3><ul>%s</ul></div>' % (cls, label, lis)

    return (
        '<section class="rules"><div class="rules-hd">'
        "<span>HOUSE RULES</span><span>%d</span></div>"
        '<div class="rules-body">%s%s</div></section>'
    ) % (
        len(buckets["always"]) + len(buckets["never"]),
        col("ALWAYS", buckets["always"], "always"),
        col("NEVER", buckets["never"], "never"),
    )


def cmd_build(args):
    lib = Library(args.root)
    lib.ensure()
    refs = [
        r
        for r in lib.load_refs()
        if _matches(r, args.collection, split_list(args.tags), args.query)
    ]
    out = Path(args.out).expanduser() if args.out else lib.root / "board.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    embed = args.embed or (out.parent.resolve() != lib.root.resolve())

    tax = lib.load_taxonomy()
    collections = {}
    for r in refs:
        collections[r.get("collection", "unsorted")] = (
            collections.get(r.get("collection", "unsorted"), 0) + 1
        )

    chips = ['<button class="chip active" data-f="*">ALL <em>%d</em></button>' % len(refs)]
    for name, count in sorted(collections.items(), key=lambda kv: (-kv[1], kv[0])):
        chips.append(
            '<button class="chip" data-f="%s">%s <em>%d</em></button>'
            % (esc(name), esc(name.upper()), count)
        )

    cards = []
    for r in refs:
        src = _img_src(r, out.parent, embed)
        if src:
            media = '<img loading="lazy" src="%s" alt="%s">' % (esc(src), esc(r.get("title")))
        else:
            media = '<div class="noimg">no capture</div>'
        tags = "".join('<span class="tag">%s</span>' % esc(t) for t in r.get("tags", []))
        host = urlparse(r.get("url", "")).netloc.replace("www.", "")
        title = esc(r.get("title"))
        head = (
            '<a class="ttl" href="%s" target="_blank" rel="noopener">%s</a>' % (esc(r["url"]), title)
            if r.get("url")
            else '<span class="ttl">%s</span>' % title
        )
        why = '<p class="why">%s</p>' % esc(r["why"]) if r.get("why") else ""
        cards.append(
            '<article class="card" data-c="%s" data-s="%s">'
            '<div class="shot">%s</div>'
            '<div class="meta"><div class="row">%s<span class="src">%s</span></div>'
            "%s<div class=tags>%s</div></div></article>"
            % (
                esc(r.get("collection", "unsorted")),
                esc(" ".join([r.get("title", ""), r.get("collection", "")] + r.get("tags", [])).lower()),
                media,
                head,
                esc(host),
                why,
                tags,
            )
        )

    tmpl = (Path(__file__).resolve().parent.parent / "assets" / "board_template.html").read_text(
        encoding="utf-8"
    )
    html = (
        tmpl.replace("{{TITLE}}", esc(args.title or "Taste Board"))
        .replace("{{SUBTITLE}}", esc(args.subtitle or "%d references" % len(refs)))
        .replace("{{RULES}}", _rules_html(lib.root))
        .replace("{{CHIPS}}", "\n".join(chips))
        .replace("{{CARDS}}", "\n".join(cards) or '<p class="none">Nothing here yet.</p>')
        .replace("{{GENERATED}}", esc(now_iso()))
    )
    out.write_text(html, encoding="utf-8")
    print(str(out))
    return 0


# --------------------------------------------------------------------- main


def main(argv=None):
    p = argparse.ArgumentParser(prog="tb", description=__doc__.splitlines()[0])
    p.add_argument("--root", default=str(default_root()), help="library root")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add a reference (captures the URL by default)")
    a.add_argument("--url")
    a.add_argument("--image", help="use an existing screenshot instead of capturing")
    a.add_argument("--clipboard", action="store_true",
                   help="read the image off the system clipboard (for pasted screenshots)")
    a.add_argument("--title")
    a.add_argument("--slug")
    a.add_argument("--collection")
    a.add_argument("--tags")
    a.add_argument("--why", help="one line: what is worth stealing here")
    a.add_argument("--viewport", default="1440,900")
    a.add_argument("--full-page", action="store_true")
    a.add_argument("--wait", type=int, default=2,
                   help="seconds to let the page settle; raise for slow/animated pages")
    a.add_argument("--engine", choices=["auto", "playwright", "chrome"], default="auto")
    a.add_argument("--no-capture", action="store_true")
    a.add_argument("--force", action="store_true")
    a.set_defaults(func=cmd_add)

    rc = sub.add_parser("recapture", help="re-shoot an existing reference")
    rc.add_argument("slug")
    rc.add_argument("--viewport", default="1440,900")
    rc.add_argument("--full-page", action="store_true")
    rc.add_argument("--wait", type=int, default=8)
    rc.add_argument("--engine", choices=["auto", "playwright", "chrome"], default="auto")
    rc.set_defaults(func=cmd_recapture)

    br = sub.add_parser(
        "browse",
        help="open a URL in a visible Chrome so the user can clear a cookie/bot wall",
    )
    br.add_argument("--url", required=True)
    br.add_argument("--timeout", type=int, default=300)
    br.set_defaults(func=cmd_browse)

    ru = sub.add_parser("rules", help="show house rules and whether they've gone stale")
    ru.add_argument("--show", action="store_true", help="print the file contents too")
    ru.add_argument("--set-derived", action="store_true",
                    help="replace the derived section with stdin, then mark it fresh")
    ru.add_argument("--mark-derived", action="store_true",
                    help="record that the derived section was just regenerated")
    ru.add_argument("--threshold", type=int, default=3,
                    help="new references before the rules count as stale")
    ru.set_defaults(func=cmd_rules)

    l = sub.add_parser("list", help="list references")
    l.add_argument("--collection")
    l.add_argument("--tags")
    l.add_argument("--query")
    l.add_argument("--json", action="store_true")
    l.set_defaults(func=cmd_list)

    t = sub.add_parser("tag", help="edit a reference's tags/collection/why")
    t.add_argument("slug")
    t.add_argument("--add")
    t.add_argument("--remove")
    t.add_argument("--collection")
    t.add_argument("--why")
    t.add_argument("--title")
    t.set_defaults(func=cmd_tag)

    r = sub.add_parser("rm", help="delete a reference")
    r.add_argument("slug")
    r.set_defaults(func=cmd_rm)

    x = sub.add_parser("taxonomy", help="show or describe collections and tags")
    x.add_argument("--describe", help='e.g. "collection:print-tech=Editorial print feel"')
    x.add_argument("--json", action="store_true")
    x.set_defaults(func=cmd_taxonomy)

    b = sub.add_parser("build", help="render the HTML board")
    b.add_argument("--out")
    b.add_argument("--title")
    b.add_argument("--subtitle")
    b.add_argument("--collection")
    b.add_argument("--tags")
    b.add_argument("--query")
    b.add_argument("--embed", action="store_true", help="inline images (portable single file)")
    b.set_defaults(func=cmd_build)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
