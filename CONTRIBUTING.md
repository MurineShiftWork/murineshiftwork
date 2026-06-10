## Contributing

Contributions are absolutely encouraged, for bug fixes, new features, etc.

If you are not sure where to start, check out the [issues](https://github.com/larsrollik/murineshiftwork/issues).

Please get in touch via [email](mailto:lars@rollik.me) for other queries.

---

## Code style

- Comments only when the WHY is non-obvious (hidden constraint, workaround, subtle invariant). No comments explaining what the code does.
- No multi-line docstrings or comment blocks; one short line max.
- No `# ====` or `# ----` section-divider lines in Python source.
- No backwards-compatibility shims for removed code — delete cleanly.
- No error handling for impossible cases; trust framework guarantees.
- No new files unless the feature genuinely requires them.

---

## Repository layout — off-limits directories

- `external/` — separate git repos mounted here; submit changes via their own PRs, not via murineshiftwork PRs.
- `murineshiftwork_v1/` — legacy reference archive; do not modify or delete.

---

## Documentation sync

Every PR that adds, removes, or changes a user-facing feature **must** update the relevant
doc in `docs/` as part of the same PR. "User-facing" means CLI flags, task parameters,
config structure, task modes, file formats, hardware behaviour.

Quick reference:

| Change | Doc to update |
|---|---|
| CLI flag / subcommand | `docs/cli/<command>.md` |
| New task or task mode | `docs/cli/tasks.md` |
| Config overlay or priority chain | `docs/concepts/config_system.md` |
| Session file format | `docs/concepts/session_files.md` |
| Hook API change | `docs/concepts/hook_system.md` |
| Setup YAML field | `docs/setup/setup_config.md` |
| Plugin or architecture decision | `docs/work_plans/` |

PRs that leave docs out of sync will be asked to update before merge.

---

## Key design docs

Read these before working on CLI, UI, or agent features:

- `docs/work_plans/IMPLEMENTATION_PLAN.md` — package split and stage breakdown
- `docs/work_plans/PLAN_msw_ui_agent_broadcast.md` — locked UI/agent architecture (Vue 3, PlotSpec, polling transport)
- `docs/concepts/plugin_system.md` — plugin entry-point contracts (`msw.host`, `msw.cli`)
- `docs/work_plans/ROADMAP.md` — current TODO / DONE list
