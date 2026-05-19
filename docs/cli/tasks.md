# msw tasks

Inspect and manage bundled task configurations.

## Subcommands

### list

```bash
msw tasks list [--filter <fragment>] [--config-dir <path>]
```

Lists all available task names grouped as Tasks, Calibration, and Tests. Shows `[overlay]` if a
`task.yaml` override exists in the config-dir overlay tree for that task.

### defaults

```bash
msw tasks defaults <task_name>
```

Prints the bundled `task.yaml` defaults for the named task. Accepts partial names (same matching
as `msw run -t`). Use this to see all parameters and their defaults before writing an overlay.

### modes

```bash
msw tasks modes <task_name>
```

Lists the named task modes defined in the task's `task.yaml` (e.g. `habituation`, `expert`,
`probe`). Activate a mode with `msw run -t <task> --task-mode <mode>`.

### init-configs

```bash
msw tasks init-configs [--config-dir <path>] [--force]
```

Copies bundled `task.yaml` files to `<config_dir>/tasks/<task_name>/task.yaml` for local
customisation. Does not overwrite existing overlays unless `--force` is given.

## Available tasks

Use `msw run -t <partial_name>` — names are matched by partial string.

| Task name | Description |
|---|---|
| `sequence` | Auditory sequence discrimination with level progression |
| `probabilistic_switching` | Two-armed bandit, free-choice ports |
| `probabilistic_switching_fixedsubjects` | Two-armed bandit, fixed lick-port assignment per subject |
| `sequence_automated` | Automated sequence (no bpod UI required) |
| `airpuff` | Airpuff conditioning |
| `optotagging` | Optogenetic tagging — multi-protocol loop (laser + TTL) |
| `_test_flush_water` | Flush water valves (maintenance) |
| `_test_stage_move` | Manual stage movement test |
| `_calibration_liquid_static` | Valve calibration — static drop count per time point |
| `_calibration_liquid_dynamic` | Valve calibration — dynamic multi-drop measurement |

## Named task modes

Modes override specific default parameters. Activate with `--task-mode <mode>`.

| Task | Modes |
|---|---|
| `probabilistic_switching` | `habituation`, `expert`, `probe` |
| `probabilistic_switching_fixedsubjects` | `habituation`, `expert`, `probe`, `stage00habituation`, `retraining` |
| `sequence` | `habituation`, `expert`, `probe` |
| `airpuff` | `habituation` |
| `optotagging` | per-protocol settings in `stimulation_protocols` list |

See [Tutorial: Adding a Subject](../tutorials/adding_subject.md) for how sticky task modes are
saved per-subject and persist across sessions.
