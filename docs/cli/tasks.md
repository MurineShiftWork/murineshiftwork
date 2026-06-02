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
| `optotagging` | Optogenetic tagging — multi-protocol loop (laser + TTL). PulsePal channels use 0-based indexing (`channels_stimulation: [0]` = output channel 1). |
| `exp_trn_spindle` | Spindle-induction training protocol |
| `sleep_homecage` | Homecage sleep recording with periodic sync barcodes |
| `openfield` | Open-field tracking |
| `periodic_trigger` | Periodic TTL trigger with sync barcodes at configurable intervals |
| `periodic_trigger_with_video` | Periodic TTL trigger + camera recording with sync barcodes |

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
| `_test_pulsepal_connect` | Minimal PulsePal connection test — prints firmware version, model, and channel counts |
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

## Optotagging waveform shaping

By default every protocol uses rectangular pulses. Set waveform params under `stimulation_defaults`
or per-protocol to replace the rectangular pulse with a three-phase shaped waveform:

```
|<-- on_ramp -->|<--- center --->|<-- off_ramp -->|
0               target_voltage   target_voltage   0
```

The total pulse duration is computed from the three phases — do not set `pulse_duration` manually
when waveform params are active.

| Parameter | Default | Description |
|---|---|---|
| `waveform_on_ramp_type` | `null` | Ramp shape for onset: `linear`, `sine`, `raised_cosine`. `null` disables the on-ramp (hard step). |
| `waveform_on_ramp_duration_s` | `0.0` | Duration of the on-ramp in seconds. |
| `waveform_center_duration_s` | `0.0` | Duration of the flat plateau at target voltage. Set to `0.0` with both ramps active for a pure bump (no flat top). |
| `waveform_off_ramp_type` | `null` | Ramp shape for offset: `linear`, `sine`, `raised_cosine`. `null` = hard step off. |
| `waveform_off_ramp_duration_s` | `0.0` | Duration of the off-ramp in seconds. |

Ramp shapes (all normalize 0 to 1 over the ramp duration):

| Shape | Formula | Character |
|---|---|---|
| `linear` | `t` | Constant slope |
| `sine` | `sin(pi/2 * t)` | Slow start, fast finish |
| `raised_cosine` | `(1 - cos(pi*t)) / 2` | Slow start and finish, fastest at midpoint |

**Pure sine bump** (no plateau): set `center_duration_s: 0.0` with the same ramp type on both sides.

**Validation:** the sum of all three phases must not exceed `1 / pulse_frequency`. A startup error
is raised if the waveform is longer than the pulse cycle.

**Ramp-sweep diagnostic mode:** the built-in `ramp_sweep` mode runs five protocols with
decreasing on-ramp durations (10 ms down to rectangular reference, 10 trials each) to compare
artifact profiles before committing to a ramp for real sessions. Activate with `--task-mode ramp_sweep`.
