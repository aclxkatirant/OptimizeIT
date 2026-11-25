# OptimizeIT

An AI agent skill that makes an existing application faster, lighter and more stable **without breaking its functionality**.

OptimizeIT is not a best-practices checklist. It learns the project, finds the real bottlenecks, prioritizes them, takes a baseline, applies targeted optimizations, validates them with tests/lint/type checks/builds, re-measures under the same conditions and produces a detailed report.

**Analyze → optimize → test → measure → report.**

## Supported Agents

| Agent | User-level directory | Project-level directory | Alternative |
|---|---|---|---|
| Claude Code | `~/.claude/skills/optimizeit` | `.claude/skills/optimizeit` | Install as a plugin |
| Codex | `~/.agents/skills/optimizeit` | `.agents/skills/optimizeit` | Older versions: `~/.codex/skills` |
| Cursor | `~/.cursor/skills/optimizeit` | `.cursor/skills/optimizeit` | Cursor also reads `.claude/skills` |
| Gemini CLI | `~/.gemini/skills/optimizeit` | `.gemini/skills/optimizeit` | Install as an extension |

All four use the open [Agent Skills](https://agentskills.io/specification) format (`SKILL.md` plus supporting files), so a single skill folder works in every one of them.

## Installation

### With the install script (all agents)

```sh
git clone https://github.com/aclxkatirant/OptimizeIT.git
cd OptimizeIT
sh install.sh                          # all four agents, user level
sh install.sh --target cursor          # a single agent
sh install.sh --project ../my-project  # into a specific project
```

Windows (PowerShell):

```powershell
.\install.ps1
.\install.ps1 -Target codex
.\install.ps1 -Project ..\my-project
```

`--target` / `-Target` values: `claude`, `codex`, `cursor`, `gemini`, `all` (default).

### As a Claude Code plugin

```
/plugin marketplace add aclxkatirant/OptimizeIT
/plugin install optimizeit@optimizeit
```

### As a Gemini CLI extension

```sh
gemini extensions install https://github.com/aclxkatirant/OptimizeIT
```

> Agent Skills may be an experimental feature in your Gemini CLI version. If the skill does not appear, enable skills in settings, run `/skills reload`, and confirm with `/skills list`.

## Usage

The skill activates automatically on performance-related requests, for example:

- "Optimize this project."
- "The `/api/orders` endpoint is too slow, speed it up."
- "Startup takes 6 seconds, find the bottleneck."
- "The frontend bundle is huge."
- "Memory keeps growing, is there a leak?"

To invoke it directly: `/optimizeit` in Claude Code and Cursor; in other agents, ask to "use the OptimizeIT skill".

## Workflow

| Phase | What happens |
|---|---|
| 1. Discovery | Languages, frameworks, architecture, entry points, databases, commands |
| 2. Analysis | Checklist plus profiling; suspicious patterns judged in context |
| 3. Prioritization | CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL, ordered by value/risk |
| 4. Baseline | "Before" measurement with a repeatable command |
| 5. Optimization | One finding at a time, behavior preserved |
| 6. Validation | Tests, lint, type checks, build, behavior comparison |
| 7. Benchmark | "After" measurement under the same conditions, noise analysis |
| 8. Report | Structured 10-section report |

## Safety Principles (summary)

- Benchmark results are never invented; unmeasured improvements are reported as "not measured".
- Tests that were not run are never reported as passing.
- Destructive database migrations are never applied automatically.
- Public APIs, configuration behavior and UI are not changed without authorization.
- Functionality and security checks are never removed for performance.
- New dependencies, schema changes and behavior changes require approval.

## Repository Layout

```
skills/optimizeit/
  SKILL.md                   Skill definition and workflow
  references/                Detailed per-phase guides
  scripts/discover.py        Project discovery script
  scripts/measure.py         Benchmark runner and comparison script
.claude-plugin/              Claude Code plugin and marketplace manifests
gemini-extension.json        Gemini CLI extension manifest
install.sh / install.ps1     Multi-agent install scripts
```

The scripts use only the Python 3.8+ standard library.

## License

MIT
