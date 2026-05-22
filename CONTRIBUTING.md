## Contributing

Contributions are absolutely encouraged, for bug fixes, new features, etc.

If you are not sure where to start, check out the [issues](https://github.com/larsrollik/murineshiftwork/issues).

Please get in touch via [email](mailto:L.B.Rollik@protonmail.com) for other queries.

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
| Setup YAML field | `docs/setup/setup_config.md` |

PRs that leave docs out of sync will be asked to update before merge.
