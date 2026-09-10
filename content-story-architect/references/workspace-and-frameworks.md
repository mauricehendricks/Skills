# Workspace Setup and Framework Management

## Workspace model

Use one private workspace named `content-storytelling-kit`, separate from the installed skill:

```text
content-storytelling-kit/
├── frameworks/   # User-created frameworks only
├── content/      # Canonical creative artifacts
├── references/   # User examples and supporting material
└── sessions/     # Resumable checkpoints and temporary alternatives
```

The skill's bundled references are immutable during normal use. The private workspace may be created anywhere the user chooses.

## Setup workflow

1. Ask where to create or reconnect the workspace only when no location is configured and the current request requires it.
2. Run `python3 scripts/setup_workspace.py --path <chosen-path>` from the skill directory.
3. Never overwrite existing files. The script may create missing standard directories.
4. Use `python3 scripts/setup_workspace.py --show` to retrieve the configured path.
5. Use `python3 scripts/setup_workspace.py --check` to validate it.

Setup configures storage only. Do not require a creator profile, niche questionnaire, or project structure.

## Framework operations

Support listing, reading, drafting, validating, saving, editing, renaming, archiving, and deleting custom frameworks. Perform only the requested operation.

Custom frameworks may be entirely original or inspired by a bundled framework. Every custom framework must contain semantically valid sections:

1. **Purpose** — The storytelling outcome the framework is designed to create.
2. **Structure** — Ordered, named beats with explanations of what each beat accomplishes.
3. **Best fit** — The content types and situations where the framework is useful.
4. **Key rule** — The most important constraint that protects the framework from misuse.

Optional examples and supporting notes may follow.

Use this template:

```markdown
# Framework Name

- **Purpose:**
- **Structure:**
  1. **Beat Name (Function):**
  2. **Beat Name (Function):**
- **Best fit:**
- **Key rule:**
```

## Creation and review

1. Understand the user's intended storytelling effect and source notes.
2. Determine whether the proposal is coherent and distinct enough to save. It does not need to extend a built-in framework.
3. Draft all four required sections while preserving meaningful original language and examples.
4. Present the proposed framework for approval before saving when the user is still exploring its design.
5. Choose a lowercase hyphenated filename that does not collide with a bundled or custom framework.
6. Save it only beneath the configured workspace's `frameworks/` directory.
7. Run `python3 scripts/validate_framework.py <file>` from the skill directory.
8. Review semantic quality manually; structural validation alone cannot prove that the framework works.

## Protection rules

- Never edit, overwrite, rename, or delete files inside the installed skill's `references/` directory through Framework Management.
- Never allow a custom framework to use the exact name or identifier of a bundled framework.
- When the user requests a modification to a built-in framework, create a clearly named custom variant in the private workspace.
- Before destructive custom-framework operations, resolve the exact file inside the configured `frameworks/` directory and follow applicable confirmation rules.
