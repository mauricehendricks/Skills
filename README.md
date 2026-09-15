# Skills

A growing collection of reusable agent skills for a wide range of tasks and workflows. Each skill lives in its own directory with a `SKILL.md` entry point and any supporting references, scripts, or assets.

## Available skills

| Skill | Purpose |
| --- | --- |
| [Content Story Architect](content-story-architect/SKILL.md) | Develop content ideas, expand seeds into distinct Idea Clusters, and create hooks, scripts, and revisions using storytelling frameworks and progression mechanics. |

## Using a skill

Install with the universal skills installer:

```bash
npx skills@latest add mauricehendricks/skills
```

Choose the skills and supported agents you want during installation.

Open a skill's directory for its instructions and supporting documentation. To install manually, copy that directory into the skills directory supported by your agent.

## Content Story Architect

Includes Idea Cluster mode, a bundled storytelling playbook, progression mechanics, a generic scriptwriting system, workspace setup, and support for private custom frameworks.

The installed skill remains separate from the user's private `content-storytelling-kit` workspace. Personal content, custom frameworks, references, and session files are not stored in this repository.

Requires an Agent Skills-compatible client and Python 3.10 or newer for the optional workspace and framework utilities.

## License

This repository is licensed under the [MIT License](LICENSE).
