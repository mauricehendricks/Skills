# Interop: DESIGN.md and installed design skills

taste-board's direction comes from its own curated library and nothing else. It does not
mine project design systems for taste — a `DESIGN.md` records what one project committed
to, which is frequently a client's brand rather than the user's preference.

So this document is narrow. It exists for one situation: **the user has asked taste-board
to write or edit a `DESIGN.md`.** That's the only time these schemas matter.

The rest of the time, the answer is simpler than anything below — deliver the brief in
conversation and let whatever owns the project's design system apply it.

## Contents

- [Detect what's installed](#detect-whats-installed)
- [DESIGN.md](#designmd)
- [PRODUCT.md — out of scope](#productmd--out-of-scope)
- [.impeccable/design.json](#impeccabledesignjson)
- [Merging without clobbering](#merging-without-clobbering)
- [What lives where](#what-lives-where)
- [Precedence](#precedence)
- [When nothing is installed](#when-nothing-is-installed)

## Detect what's installed

Check the project and the user's home before deciding where rules go. Agents keep skills
in different directories, so probe the known locations rather than assuming one — this
covers Claude Code, Cursor, Codex, Copilot/VS Code, Gemini, OpenCode, and the shared
`.agents` hub, in both project and home scope:

```bash
ls DESIGN.md PRODUCT.md 2>/dev/null
for d in .agents .claude .cursor .github .codex .gemini .opencode; do
  for base in . "$HOME"; do
    find "$base/$d/skills" -maxdepth 1 \
      \( -iname '*impeccable*' -o -iname '*taste*' \) 2>/dev/null
  done
done | grep -v taste-board
```

(`find` rather than a glob — an unmatched `ls` glob is a fatal error in zsh and would
bury the real result in shell noise.)

What the hits mean:

- **`DESIGN.md` exists** → the project already has a committed design system. Read it and
  let it constrain the brief. This is the single most important signal; it outranks
  anything you'd infer from the library. Don't edit it unless asked.
- **`impeccable` installed** → it owns `DESIGN.md` + `PRODUCT.md` and has its own
  commands (`/impeccable init`, `/impeccable document`). If neither file exists yet,
  prefer suggesting the user run `/impeccable init` and then enrich the result, rather
  than racing it with a file of your own shape.
- **`taste-skill` installed** → it reads `SKILL.md`-style guidance and exports the same
  `DESIGN.md` format. Same target file, no special handling.
- **Nothing** → see [When nothing is installed](#when-nothing-is-installed).

## DESIGN.md

An open format from Google Labs (Apache-2.0) — YAML tokens for machines, prose for
rationale. Both impeccable and taste-skill target it, which is why it's the handoff point.

The prose headings have a **mandated order**. Keep it; tools parse by heading:

1. `## Overview` (alias: Brand & Style)
2. `## Colors`
3. `## Typography`
4. `## Layout` (alias: Layout & Spacing)
5. `## Elevation & Depth` (alias: Elevation)
6. `## Shapes`
7. `## Components`
8. `## Do's and Don'ts`

Frontmatter carries `version`, `name`, `description`, and token groups: `colors`,
`typography`, `rounded`, `spacing`, `components`. Tokens follow W3C DTCG shapes.

Shape of the file:

```markdown
---
version: 1
name: Acme
description: Print-derived editorial system, near-monochrome with one warm accent.
colors:
  primary: "#1A1C1E"
  accent: "#B4471F"
  surface: "#F4F1EC"
typography:
  display:
    fontFamily: "GT Sectra"
    fontSize: "72px"
    lineHeight: "1.05"
    letterSpacing: "-0.02em"
  microlabel:
    fontFamily: "iA Writer Mono"
    fontSize: "10.5px"
    letterSpacing: "0.16em"
rounded:
  sm: "2px"
  md: "3px"
spacing:
  sm: "8px"
  md: "22px"
---

## Overview

Near-monochrome paper ground, one warm accent, type at extremes. Derived from
12 references in the `editorial` collection — see `~/.taste-board/board.html`.

## Colors

Primary (#1A1C1E): deep ink for headlines and body. Accent (#B4471F) appears at most
once per viewport — in every reference that uses it, it marks exactly one thing.

...

## Do's and Don'ts

### Do:
- Anchor each page on one monumental image with timeless subject matter.

### Don't:
- Use purple gradients or glossy 3D shapes.
```

Four things worth getting right:

- **`## Do's and Don'ts` is where Always/Never goes**, split into `### Do:` and
  `### Don't:` lists. It's already in the spec, so don't invent a "House DNA" section
  next to it. Mirror `rules.md`'s bullets here.
- **Components reference tokens, they don't restate them.** Real files use
  `backgroundColor: "{colors.starlight-blue}"`, not a repeated hex. Follow whatever
  the existing file does — a literal hex where siblings use references reads as a bug.
- **Cite references in the prose.** "Derived from 12 references in `editorial`" or a
  named slug turns an assertion into something the user can check and argue with.
- **Match the existing naming style.** A file whose colors are `deep-space-black` and
  `nebula-violet` should not gain a `primary-2`. Names carry intent.

Only emit tokens you can actually justify from the captures. A confidently wrong hex is
worse than an omission — the spec has an `omitted` key for sections you're leaving out.

## PRODUCT.md — out of scope

Impeccable's companion file: audience, positioning, brand commitments, behind a
`<!-- impeccable:product-schema 1 -->` marker. **Never write it.** A taste board has
evidence about how things should *look*, not about who a product is for — that's
impeccable's territory and it has an interview flow for gathering it.

Read it when it's there, though. It's cheap context and `## Brand Commitments` in
particular pins down palette, typeface, and official naming — facts that constrain any
visual suggestion you'd make.

One correction worth knowing, since impeccable's docs mislead here: they describe
`PRODUCT.md` as holding **anti-references**, but schema 1 has no such heading. Its
sections are `Platform` · `Users` · `Product Purpose` · `Positioning` ·
`Operating Context` · `Capabilities and Constraints` · `Brand Commitments` ·
`Evidence on Hand` · `Product Principles` · `Accessibility & Inclusion`. Visual negatives
live in `DESIGN.md`'s `## Do's and Don'ts` under `### Don't:` — that's the real home for
everything a taste board produces on the negative side.

## .impeccable/design.json

If `.impeccable/` exists, `design.json` is a generated machine-readable mirror of
`DESIGN.md` (`schemaVersion`, `generatedAt`, `title`, `extensions`, `components`,
`narrative`). **Never hand-edit it** — edit `DESIGN.md` and let `/impeccable document`
regenerate it, or the two silently disagree and the JSON usually wins downstream.

Its presence is also the strongest possible signal that impeccable owns these files:
follow the existing structure exactly rather than improving on it.

## Merging without clobbering

Only relevant once the user has asked you to write. Treat these files as theirs:

1. Read the file first. Always.
2. **If impeccable owns it, prefer handing the brief to `/impeccable document` over
   editing directly.** A direct edit is discarded the next time impeccable regenerates,
   and it desyncs `DESIGN.md` from `.impeccable/design.json` in the meantime.
3. Add to sections that exist; don't reorder or rewrite prose you didn't write.
4. Never add a heading the schema doesn't define — off-schema sections get dropped.
5. When replacing a value the user wrote, show the diff and ask.
6. Keep additions attributable: `<!-- taste-board: editorial collection, 12 refs -->`
   above a block you generated makes the next merge tractable.
7. Never delete a section to "clean up." If something looks stale, mention it.

## What lives where

Global and project files answer different questions, so they don't compete:

| | Lives in | Holds | taste-board may |
|---|---|---|---|
| `rules.md` | `~/.taste-board/` | Generic taste — hand-written half + derived half | own it |
| `refs/`, `taxonomy.json` | `~/.taste-board/` | The reference library and its vocabulary | own it |
| `DESIGN.md` | **project root** | This product's tokens, type, components | read; write if asked, or if absent |
| `PRODUCT.md` | **project root** | Audience, positioning, brand commitments | read only — never write |

**Never write `DESIGN.md` or `PRODUCT.md` into `~/.taste-board/`.** They describe a
specific product, belong in version control next to the code they govern, and are
routinely shared with collaborators and clients who have nothing to do with the user's
personal library. A global `DESIGN.md` would also silently leak one client's brand into
the next project, which is the worst possible failure here.

The global side stays deliberately generic: "type at extremes," "one accent per
viewport," "never icon-grid feature rows." Craft standards, not brand decisions. If
something belongs to one client, it goes in that project's `DESIGN.md`.

## Precedence

**taste-board influences; it never overrides.** The board shapes the overall direction
and the patterns you reach for. The human, and whatever governs this specific repo, always
outrank it:

1. What the user tells you in conversation
2. The project's own files and skills — `DESIGN.md`, `PRODUCT.md`, `impeccable`,
   `taste-skill`, repo conventions
3. `~/.taste-board/rules.md` and patterns synthesized from the library — **influence**
4. Generic craft defaults

There's no scope carve-out where the global library wins. Even a craft standard the user
wrote by hand yields to the project, because a repo's design system is a commitment made
in a specific context, while the library is a record of what caught their eye.

**On conflict, stop and ask. Don't resolve it yourself.** Not for brand collisions
specially — for any conflict. "Your rules say near-monochrome with one warm accent; this
project's `DESIGN.md` commits to two brand glows. Which governs here?" is a thirty-second
question that prevents work the user won't recognize.

Silently picking a side is the failure mode, and it's worse in this direction than most:
the user can't see the library and the project file side by side the way you can, so a
quiet resolution looks like the skill simply having bad taste.

When something does resolve cleanly, still **say which source won.**

## When nothing is installed

*Offer* to write `DESIGN.md` at the project root — don't just do it. It's a documented
open format, costs nothing if unused, and both impeccable and taste-skill will pick it up
later, so the work isn't wasted. But it's still a file appearing in someone's repo root,
and which parts of a personal taste library should become a project's committed design
system is the user's call, not an inference you make on their behalf.

Mention the tools once, without pushing:

- impeccable — https://impeccable.style/ — `npx skills add pbakaus/impeccable`
- taste-skill — https://www.tasteskill.dev/ — `npx skills add Leonxlnx/taste-skill`
- DESIGN.md spec — https://github.com/google-labs-code/design.md
