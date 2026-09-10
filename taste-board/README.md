# taste-board

A local, durable library of design references — a moodboard for web work that turns into
rules your coding agent actually builds from.

Taste is gathered slowly and lost instantly. You bookmark a site, describe it once in a
prompt, and by the next project it's gone. `taste-board` keeps references in one place,
makes them searchable, and distills them into generic design rules that regenerate as the
library grows — so your agent starts from your taste instead of a blank prompt.

It's an [Agent Skill](https://agentskills.io), so it works in Claude Code, Cursor, Codex,
Gemini CLI, Copilot, OpenCode, Goose, and any other skills-compatible agent.

## Install

```bash
npx skills add mauricehendricks/skills --skill taste-board
```

Or drop the folder into your agent's skills directory yourself — `.claude/skills/`,
`.cursor/skills/`, `.agents/skills/`, `.github/skills/`, whichever your tool reads.

**Requirements:** Python 3.8+ (stdlib only) and a Chromium-family browser — Chrome, Edge,
Brave, or Chromium — for screenshots. Both are auto-detected on macOS, Linux, and Windows.
Clipboard reading is built in on macOS and Windows; on Linux it needs `wl-clipboard`
(Wayland) or `xclip` (X11).

There's no setup step and nothing to configure. If something is missing, the error that
hits you names it and carries the fix command for your platform. Nothing here installs
anything on your behalf — a skill is a folder of instructions that lands on your machine
without executing, and it should stay that way.

## Use it

Talk to your agent. The skill triggers on things like:

> save this for inspiration — https://example.com
>
> what's my design direction for this project?
>
> pull together a moodboard for the new landing page

Or drive the script directly:

```bash
# add a reference, capturing a screenshot
python3 scripts/tb.py add --url https://example.com \
  --collection editorial --tags "mono labels,hairline rules" \
  --why "Rules instead of card borders — the whole page holds together without boxes."

# add the screenshot you just pasted / copied
python3 scripts/tb.py add --clipboard --title "Some Studio"

# or one you already have on disk
python3 scripts/tb.py add --image ~/Desktop/shot.png --title "Some Studio"

# browse and filter
python3 scripts/tb.py list --collection editorial
python3 scripts/tb.py taxonomy

# render the board
python3 scripts/tb.py build
python3 scripts/tb.py build --tags "mono labels" --embed --out ./design/board.html
```

On Windows use `python` if `python3` isn't on your PATH.

## What it does

**Captures** references from URLs (headless Chrome), from the system clipboard when you've
just pasted a screenshot, or from a file on disk. Every path copies the image into the
library, so a reference never depends on the original surviving.

**Tags** them two ways: one *collection* per reference for the aesthetic family, and many
*tags* for the specific moves worth stealing. The skill pushes toward tags that name a
decision — "hairline rules instead of card borders" — over vibes like "clean," which match
everything and therefore filter nothing.

**Renders** a self-contained HTML board: your Always/Never rules up top, filter chips per
collection, searchable card grid, light and dark.

**Derives** generic rules from the library into `rules.md`, and **regenerates** them as it
grows — ten references reveal patterns three don't. The file has a hand-written half that's
yours and a derived half that gets rewritten; `tb.py rules` reports when it's gone stale.

### When a capture is blocked

Consent walls and bot checks are common, and a screenshot of a cookie dialog is still a
valid PNG — so exit codes won't catch it. The skill has the agent look at every capture
and, when something's in the way, stop and offer you the choice: clear it once in a
visible browser (`tb.py browse --url ...`, which persists the cookies for later
captures), take over a browser the agent already has open, or screenshot it yourself.
It won't quietly file a card whose image is a cookie banner.

## Where things live

Global and project files answer different questions, so they don't compete:

| | Location | Holds |
|---|---|---|
| Library + `rules.md` | `~/.taste-board` (see below) | References, and your generic cross-project taste |
| `DESIGN.md` | project root | That product's tokens, type, components |
| `PRODUCT.md` | project root | Audience and positioning — impeccable's; taste-board never writes it |

The library is curated **only** by what you deliberately add. It doesn't scan your repos
or infer taste from project design systems — a `DESIGN.md` records what one project
committed to, often a client's brand rather than your preference, and nothing tells the
two apart. If a shipped system does reflect your taste, add it as a reference so it
passes the same gate as everything else.

The one link to projects is optional and one-way: when a repo has no `DESIGN.md` and
nothing else owns one, taste-board can **export a starting version** from your board. It
offers rather than assumes, and it never writes `PRODUCT.md`.

Library location, first match wins:

1. `$TASTE_BOARD_HOME`
2. `$XDG_DATA_HOME/taste-board`
3. `%LOCALAPPDATA%\taste-board` on Windows
4. `~/.taste-board` on macOS, `~/.local/share/taste-board` on Linux

## Works alongside other design skills

Complementary, not competing. taste-board answers *what does this person like* — the
evidence. [impeccable](https://impeccable.style/) and
[taste-skill](https://www.tasteskill.dev/) answer *how do we build well* — the craft. They
meet at [`DESIGN.md`](https://github.com/google-labs-code/design.md), which all three read.

[Mobbin's MCP](https://mobbin.com/mcp) is worth having too: search it to *discover*
references, then `add` the good ones here so they persist in your own vocabulary.

## Optional: Playwright

Chrome handles most sites with no install. For slow-hydrating pages and true full-page
shots, Playwright does better and is used automatically when present:

```bash
pip3 install playwright && python3 -m playwright install chromium
```

## Developing

To work on the skill and have edits apply immediately, symlink the `taste-board` folder into your
agent's skills directory instead of installing a copy:

```bash
ln -s "$(pwd)/taste-board" ~/.claude/skills/taste-board     # or ~/.codex/skills, ~/.cursor/skills, …
```

Edits are then live on the next session start — no reinstall, and no second copy to drift.

**Remove the symlink before installing normally.** Two entries for one agent will
conflict, and the one you're editing may not be the one that loads:

```bash
rm ~/.claude/skills/taste-board
npx skills add mauricehendricks/skills --skill taste-board
```

`npx skills update` does not touch a hand-made symlink — it has no record of it. Update
that install with `git pull` instead.

## Privacy

Everything is local. Captures are ordinary PNGs on disk, nothing is uploaded, and the
skill only visits pages you ask it to.

## License

MIT — see [LICENSE](LICENSE).
