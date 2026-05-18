# msw tasks

> Skeleton — `msw tasks` subcommands are planned; see ROADMAP.

Planned subcommands:

- `msw tasks list` — list all available task names
- `msw tasks defaults <name>` — print the bundled `task.yaml` defaults for a task
- `msw init task-configs` — copy bundled `task.yaml` files to the config-dir overlay tree
  for local customisation

## Available tasks (current)

Use `msw run -t <partial_name>` — task names are matched by partial string.

| Task name | Description |
|---|---|
| `sequence` | Auditory sequence discrimination |
| `probabilistic_switching` | Two-armed bandit, free-choice ports |
| `probabilistic_switching_fixedsubjects` | Two-armed bandit, fixed lick-port assignment |
| `sequence_automated` | Automated sequence (ported from MATLAB) |
| `airpuff` | Airpuff conditioning |
| `_test_flush_water` | Flush water valves (maintenance) |
| `_calibration_water_with_serial_scale` | Valve calibration with serial scale |
