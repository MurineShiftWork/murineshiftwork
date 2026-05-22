# Claude Code — Working Guidelines for murineshiftwork

Instructions for AI assistants (Claude Code) working in this repository.
Human-facing contribution notes are in CONTRIBUTING.md.

---

## Commit discipline

- **Never create git commits or tags without explicit user instruction.**
- Never amend published commits; always create a new commit.
- Never skip pre-commit hooks (`--no-verify`).

---

## Code style

- No comments unless the WHY is non-obvious (hidden constraint, workaround, subtle invariant).
- No multi-line docstrings or comment blocks.
- No backwards-compatibility shims for removed code — delete cleanly.
- No error handling for impossible cases; trust framework guarantees.
- Default: no new files unless the feature genuinely requires them.

---

## Documentation — mandatory sync rule

**Every code change that adds, removes, or modifies a user-facing feature must update the relevant docs file in the same session, before the session closes.**

User-facing means: CLI flags, task parameters, config file structure, file naming conventions, task modes, hardware behaviour.

### What to update

| Change | Doc to update |
|---|---|
| New CLI flag or subcommand | `docs/cli/<command>.md` |
| New task or task mode | `docs/cli/tasks.md` |
| New task.yaml `default:` key | `docs/cli/tasks.md` + `docs/concepts/config_system.md` if it illustrates a new pattern |
| Config overlay / priority chain change | `docs/concepts/config_system.md` |
| Session file format change | `docs/concepts/session_files.md` |
| Hook API change | `docs/concepts/hook_system.md` |
| Setup YAML field change | `docs/setup/setup_config.md` |
| New getting-started flow | `docs/getting_started/` |
| Work plan / architecture decision | `docs/work_plans/` (and memory files if relevant) |

### What does NOT need a doc update

- Internal refactors with no user-visible change
- Test additions
- Bug fixes that restore documented behaviour (not change it)
- `docs/legacy/` and `docs/work_plans/` — those are internal/planning, not user reference

### Skeleton docs

`docs/` files marked `> Skeleton — fill in` must be completed before that feature is considered done.
Remove the skeleton marker when content is added.

---

## Directories that are off-limits

- `external/` — never modify code in `external/`. Read it, copy from it, reference it, but do not edit it.
- `murineshiftwork_v1/` — legacy reference only; never delete or modify files there.

---

## Config and paths

- Live config dir: `/mnt/maindata/msw_configs` (subjects/, setups/, tasks/ overlays)
- Machine-local config: `~/.murineshiftwork/msw_machine.yaml`
- Central logs: `~/.murineshiftwork/logs/<setup>--<datetime>--<subject>--<task>.log`
- Session crash-recovery backup: `~/.murineshiftwork/sequence/` — intentional, not legacy

---

## Memory files

Memory is at `/home/murinemanager/.claude/projects/-mnt-maindata-code-murineshiftwork/memory/`.
Update memory when decisions are locked or project state changes significantly.
Index is `MEMORY.md` — keep under 200 lines.

---

## Key design docs (read before agent/UI work)

- `docs/work_plans/IMPLEMENTATION_PLAN.md` — authoritative stage breakdown, gap table, package split
- `docs/work_plans/PLAN_msw_ui_agent_broadcast.md` — locked architecture decisions (Vue 3 + Plotly.js, PlotSpec, polling transport, agents.json)
- `docs/work_plans/ROADMAP.md` — revolving TODO / DONE list
