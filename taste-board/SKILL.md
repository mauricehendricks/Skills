---
name: taste-board
description: Build and maintain a personal library of design references — a Pinterest-style taste board for web design work, stored entirely on this machine. Use this whenever the user shares a site they like the look of, pastes a design screenshot, says "save this for inspiration", "add this to my references", "what's my design direction", "put together a moodboard", "collect some inspiration for this project", or asks to browse/search/filter references they've saved before. Also use at the start of a design or redesign project to assemble a visual direction, and whenever the user wants their accumulated taste turned into concrete rules an agent can build from. Trigger even when they don't say "moodboard" or "taste board" — sharing a URL admiringly, or asking "what do I usually like", is enough.
---

# Taste Board

A durable, local library of design references, plus the machinery to turn it into
instructions other agents can build from.

The problem this solves: taste is gathered slowly and lost instantly. People bookmark
a site, describe it once in a prompt, and by the next project it's gone. This skill
makes references accumulate in one place, stay searchable, and — the part that matters
most — get distilled into rules that design skills consume.

## Where this sits relative to other design skills

Run this **alongside** design skills, not instead of them. The division of labor:

| | Question it answers | Owns |
|---|---|---|
| **taste-board** (this) | *What does the user actually like?* — evidence, gathered over time | the library, `rules.md` |
| `impeccable`, `taste-skill` | *How do we build well?* — craft rules at build time | `DESIGN.md`, `PRODUCT.md` |
| `frontend-app-builder` | *Make this specific thing* | the implementation |

taste-board is the input side, and it stays there. It gathers and organizes the evidence,
then hands the conclusions to whatever owns the project's design system — it does not
maintain that system itself. A skill that quietly rewrites another skill's files is a
skill people uninstall.

That makes the deliverable the board plus a well-argued brief, not a file write. See
[Exporting a starting DESIGN.md](#exporting-a-starting-designmd) for the one exception,
and `references/interop.md` for the schemas when the user does ask you to write.

## The library

One global library, so taste compounds across projects; individual projects get filtered
*views* rather than separate libraries.

```
<library>/
├── rules.md         generic rules: a hand-written half + a regenerated half
├── taxonomy.json    collections + tags, each with a description
├── refs/<slug>/     ref.json + capture.png
└── board.html       generated
```

The location follows platform convention: `$TASTE_BOARD_HOME`, else
`$XDG_DATA_HOME/taste-board`, else `%LOCALAPPDATA%\taste-board` on Windows, else
`~/.taste-board` on macOS and `~/.local/share/taste-board` on Linux. Run
`python3 scripts/tb.py taxonomy` once to see where it actually resolved rather than
hardcoding a path into anything.

All operations go through `scripts/tb.py` (stdlib only, Python 3.8+; use `python` instead
of `python3` where that's the name on PATH). Run `python3 scripts/tb.py <cmd> --help` for
flags. Don't hand-edit `ref.json` files — the script keeps the taxonomy in sync.

`taxonomy` prints the resolved library path, which is the reliable way to answer "where
does my stuff live" on a platform you're not sure about.

When something's missing from the environment, the error says so and carries the fix —
show the user that command rather than running it. Installing a browser or a system
package is their call, and a skill that mutates the machine it lands on is a bad guest.

## Adding references

**From a URL** — captures a 1440×900 screenshot with headless Chrome:

```bash
python3 scripts/tb.py add --url https://example.com \
  --collection "saas-marketing" --tags "restraint,strong type" \
  --why "Gradient used as one anchor, not decoration everywhere."
```

**From a screenshot the user just pasted into the conversation.** You can see the image
but have no file path for it — the bytes live in the conversation, not on disk. They're
almost always still on the system clipboard, so read them from there:

```bash
python3 scripts/tb.py add --clipboard --title "Some Studio" \
  --collection "editorial" --tags "halftone,mono labels"
```

Reach for this the moment someone pastes a design screenshot. Asking them to save the
file and hand you a path is friction at precisely the wrong moment. If the clipboard has
moved on, `--image` with a path is the fallback.

**From a file on disk:**

```bash
python3 scripts/tb.py add --image ~/Desktop/shot.png --title "Some Studio"
```

Every path — URL, clipboard, disk — **copies** the image into the library. A reference
never depends on the original surviving, so clearing the clipboard or deleting the file
afterwards is harmless.

Useful flags: `--full-page` for the whole scroll, `--viewport 1280,720`, `--no-capture`
to record a URL without an image.

Capture takes ~10s per site. When adding several, run the `add` commands in parallel.

### Look at what you captured

This is the step that makes the library worth having. After capturing, **read the PNG**
and write the tags and the `--why` from what's actually on screen — not from the domain
name or your prior knowledge of the brand. A reference you never looked at is a bookmark.

It also means you, not a heuristic, are the thing deciding whether the capture is real.

### When a capture is blocked

Some sites can't be shot cleanly headlessly — consent walls, bot checks, login gates,
region interstitials. Note that the command often reports **success** in these cases: a
screenshot of a cookie dialog is still a valid PNG. Exit codes won't catch this. You
will, by looking.

Three outcomes, and they're handled differently:

- **No image** — the command reports `BLOCKED:`. Escalate.
- **The wall is the shot** — a consent dialog, Cloudflare check, paywall, or empty
  shell fills the frame. Escalate, and don't file it. A card whose capture is a cookie
  banner is worse than no card: it pollutes the board and later synthesis passes read it
  as evidence. Nothing about a cookie banner is anyone's taste.
- **The wall covers part of a good shot** — a banner across the bottom third, masthead
  and layout clearly legible above it. Don't silently keep it and don't silently discard
  it. Say what's obscured and offer to re-shoot; if the user would rather keep it, note
  the obstruction in `--why` so a later synthesis pass doesn't read the banner as design.

When escalating, stop and tell the user what's in the way, then offer the choices —
cheapest-first, but it's their call:

1. **Clear it in a browser once.** `python3 scripts/tb.py browse --url <url>` opens a
   visible Chrome window. The user accepts the banner or clears the check, closes it,
   and the cookies persist to the taste-board profile — later captures of that site
   inherit the approval. Follow with `recapture <slug>`.
2. **You already have a browser open.** If this session has any browser tool — a
   preview/in-app browser, a Playwright or CDP session, an extension connected to the
   user's real signed-in browser — the user can take over that tab, clear the wall, and
   you retry from there. This is the right option for anything behind their login,
   since those cookies never reach a headless profile.
3. **They screenshot it themselves.** If they paste it into the conversation, file it
   with `--clipboard`; if they save it, `--image`. Best when they want a particular
   scroll position or a state you can't reach anyway.

Batch these. If six of twenty captures are blocked, don't interrupt six times — finish
the rest, then report the blocked set together with what's blocking each.

Before escalating, one cheap retry is fair: `--wait 8` fixes slow-hydrating pages, and
`--engine playwright` handles more if it's installed
(`pip3 install playwright && python3 -m playwright install chromium`). Don't retry more
than once; a bot check won't yield to persistence.

### Tagging

Two things are being recorded, and they work differently:

- **Collection** — one per reference, the aesthetic family it belongs to
  (`editorial`, `brutalist-utility`, `app-ui`). Coarse; these are the filter chips.
- **Tags** — many per reference, the specific moves worth stealing
  (`halftone texture`, `mono microlabels`, `full-bleed hero`, `single warm accent`).

Propose tags yourself, then let the user correct them — most people recognize their taste
faster than they can articulate it. **Reuse the existing vocabulary before minting new
terms.** Check `python3 scripts/tb.py taxonomy` first; a library where twelve references
each carry a unique tag can't be filtered, which defeats the point.

Prefer tags that name a *decision* over ones that name a *vibe*. "clean" and "modern"
describe nothing and match everything; "hairline rules instead of card borders" is a thing
someone can go do. When a tag would be hard to act on, ask what specifically caught
their eye.

Describe collections and tags so their meaning survives:

```bash
python3 scripts/tb.py taxonomy --describe "collection:editorial=Print-derived: rules, marginalia, mono labels"
```

Fix things up with `tag`:

```bash
python3 scripts/tb.py tag some-slug --add "dither" --remove "clean" --collection editorial
```

## Building the board

```bash
python3 scripts/tb.py build                                    # whole library
python3 scripts/tb.py build --collection editorial             # one collection
python3 scripts/tb.py build --tags "mono labels" --query hero  # narrow slice
```

For a **project view**, write it into the project and inline the images so the file is
portable and survives being moved or shared:

```bash
python3 scripts/tb.py build --tags "editorial,mono labels" --embed \
  --out ./design/taste-board.html --title "Acme — visual direction"
```

The board renders the Always/Never bullets from `rules.md` at the top, filter chips per
collection, and a searchable card grid. Open it for the user when you've built it.

## House rules — a living synthesis

`rules.md` holds the generic, cross-project rules. It has two halves that behave
differently, and the split is what makes it safe to regenerate:

- **`## Yours`** — hand-written. Never regenerated, and it wins over the derived half.
- **`## Derived`** — everything between `<!-- taste-board:derived:start -->` and
  `<!-- taste-board:derived:end -->` is rewritten wholesale from the library. Never
  hand-edit inside the markers; the next regeneration discards it.

The derived half is the point: rules should **track the library as it grows**, not
calcify at whatever the user happened to believe when they first wrote them. Ten new
references can reveal a pattern that wasn't visible at three.

The derived half has exactly **one** source: the curated references, plus what the user
tells you directly. Nothing else.

That narrowness is deliberate. Project design systems look like tempting evidence and
aren't: a repo's `DESIGN.md` records what *that project* committed to, which is often a
client's brand or a stakeholder's mandate — the compromises taste had to make, not the
taste. Inferring from it would conclude someone loves purple gradients because a client
required them, and nothing distinguishes their own project from a client's.

Every reference got into the library because the user deliberately put it there. That
gate is the value. If a shipped design system genuinely reflects their taste, the move is
to add it as a reference — screenshot, tag, `--why` — so it passes through the same gate
as everything else.

### Regenerating

`python3 scripts/tb.py rules` reports how many references have landed since the last
regeneration and whether it's gone stale. Check it when the user asks about their
direction, and after adding a batch of references.

To regenerate: read the captures, then pipe the new derived text in — this splices it
between the markers and stamps the timestamp in one step, so a stray edit can't destroy a
marker and break every future regeneration:

```bash
printf '### Always\n\n- Type at extremes\n\n### Never\n\n- Icon-grid feature rows\n' \
  | python3 scripts/tb.py rules --set-derived
```

Write only the derived body — the markers and the `## Yours` half look after themselves.
(`--mark-derived` alone just stamps the timestamp, for when you edited the file directly.)

Keep the derived half generic. It applies to every future project, so "type at extremes"
and "one accent per viewport" belong here; "the accent is `#B4471F`" does not — that's a
project decision. If a derived rule couldn't sensibly apply to a client you haven't met
yet, it's in the wrong file.

## Turning the board into a brief

When the user is starting real work — or asks what their direction is — synthesize:

1. `python3 scripts/tb.py list --json` for the relevant slice, and **read the captures**.
   Ground every claim in specific references; a brief that could have been written
   without looking at the images is worthless.
2. Find what actually recurs. Three references sharing a move is a pattern; one is a
   one-off. Say which references support each rule — that traceability is what makes the
   brief arguable instead of just assertive.
3. Write concrete values. `#1A1C1E`, `72px/1.05`, `1px hairline` — not "dark neutral",
   "large", "subtle". Vague briefs produce generic output, which is the failure mode
   this whole skill exists to prevent.
4. Capture the negative space too. What the user consistently *avoids* steers a model at
   least as hard as what they like.

The brief describes the user's taste, not this project's answer. Don't read the repo's
`DESIGN.md` to shape it — reconciling generic taste against a specific product's brand is
the consuming skill's job, and it has the product context to do it properly. If the user
points out a conflict, that's a conversation, not something to pre-empt by quietly
trimming the brief to fit.

Where the references genuinely disagree, present the split as a choice — two coherent
directions — instead of blending them into mush. Averaging two strong directions reliably
produces a weak one.

## Exporting a starting DESIGN.md

taste-board produces *generic* taste. Applying it to a specific project — reconciling it
with a brand, an audience, a stakeholder's constraints — is the job of whatever owns that
project's design system. There's no ongoing relationship to maintain, and no syncing.

One optional terminal action: **when a project has no `DESIGN.md` and nothing else owns
one, offer to export a starting version from the board.** One-way, on request.

- **Offer, don't assume.** A file appearing in someone's repo root should never be a
  surprise, and which parts of a personal library belong in a committed project system
  is their call.
- **Generic rules become a starting point, not the answer.** Say so. The export is
  scaffolding for impeccable or taste-skill to take over, not a finished brand.
- **If `DESIGN.md` already exists, don't export.** Point at the owning skill instead —
  `/impeccable document` writes it properly and keeps `.impeccable/design.json` in sync,
  whereas a direct edit gets discarded on the next regeneration.
- **If asked to edit an existing one anyway**, read it first and merge; match its heading
  structure and naming exactly, and never add an off-schema section.
  `references/interop.md` has the schema.

**`PRODUCT.md` is out of scope entirely** — never write it. It covers audience and
positioning, which a taste board has no evidence about.

The only file this skill owns outright is `rules.md` in the library, and even there the
ownership is split: you regenerate the derived half, the user writes the other.

## Notes

- Everything is local. Nothing is uploaded, and captures are ordinary PNGs on disk.
- Only capture pages the user asked for. Don't crawl a site or follow links from one.
- `Mobbin`'s MCP is complementary if installed: search it to *discover* references, then
  `add` the good ones here so they persist in the user's own vocabulary.
