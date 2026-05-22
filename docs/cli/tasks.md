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
msw tasks init-configs [task_name ...] [--config-dir <path>] [--force]
```

Copies bundled `task.yaml` files to `<config_dir>/tasks/<task_name>/task.yaml` for local
customisation. If no task names are given, all tasks are copied. Does not overwrite
existing overlays unless `--force` is given.

```bash
# Copy all tasks
msw tasks init-configs

# Copy specific tasks
msw tasks init-configs optotagging sequence --force
```

## Available tasks

Use `msw run -t <partial_name>` — names are matched by partial string. Run `msw tasks list` to see the current list with overlay markers.

### Behavioural tasks

| Task name | Description |
|---|---|
| `sequence` | Auditory sequence discrimination with level progression |
| `probabilistic_switching` | Two-armed bandit, free-choice ports |
| `probabilistic_switching_fixedsubjects` | Two-armed bandit, fixed lick-port assignment per subject |
| `airpuff` | Airpuff conditioning |
| `optotagging` | Optogenetic tagging — multi-protocol loop (laser + TTL) |
| `exp_trn_spindle` | Spindle-induction training protocol |
| `homecage_sleep` | Homecage sleep recording |
| `openfield` | Open-field tracking |
| `periodic_trigger` | Periodic TTL trigger |
| `periodic_trigger_with_video` | Periodic TTL trigger with camera recording |

### Calibration tasks

| Task name | Description |
|---|---|
| `_calibration_liquid_static` | Valve calibration — static drop count per time point |
| `_calibration_liquid_dynamic` | Valve calibration — dynamic multi-drop measurement |
| `_calibration_sound_latency` | Sound latency calibration |

### Test / maintenance tasks

| Task name | Description |
|---|---|
| `_test_flush_valves` | Flush water valves (maintenance) |
| `_test_stage_move` | Manual stage movement test |
| `_test_bpod_connect` | Minimal Bpod connection test |
| `_test_minimal_task` | Minimal task smoke test |
| `_test_video` | Camera/video recording test |
| `_test_barcode_iti` | TTL barcode + ITI test |
| `_test_barcode_iti_with_video` | TTL barcode + ITI + video test |
| `_test_trigger_with_video` | TTL trigger + video test |
| `_test_ttl_barcodes` | TTL barcode output test |
| `_test_ttl_outputs` | Generic TTL output test |

## Named task modes

Modes override specific default parameters. Activate with `--task-mode <mode>`.
Run `msw tasks modes <task>` to see the current modes for any task.

| Task | Modes |
|---|---|
| `probabilistic_switching` | `habituation`, `expert`, `probe` |
| `probabilistic_switching_fixedsubjects` | `habituation`, `expert`, `probe`, `stage00habituation`, `retraining` |
| `sequence` | `habituation`, `expert`, `probe` |
| `airpuff` | `habituation` |
| `optotagging` | per-protocol settings in `stimulation_protocols` list |
| `_test_flush_valves` | `fill`, `wash`, `test` |

See [Tutorial: Adding a Subject](../tutorials/adding_subject.md) for how sticky task modes are
saved per-subject and persist across sessions.
