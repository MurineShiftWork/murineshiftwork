# Configuration System

> Skeleton — fill in. See `docs/getting_started/quickstart.md` for usage examples.

## Config layers

Settings are resolved from multiple sources in priority order (lowest → highest):

1. **Bundled `task.yaml` defaults** — shipped with each task package
2. **Config-dir overlay** — `<config_dir>/tasks/<task>/task.yaml` deep-merges on top
3. **Task mode** — named block from `task.yaml mode:` section (sticky via subject YAML or `--task-mode`)
4. **Subject YAML `task_overrides`** — per-subject, per-task overrides
5. **CLI `-ts KEY=VALUE`** — highest priority, one-off overrides

## Named task modes

Each task can define named configuration bundles in `task.yaml`:

```yaml
default:
  REWARD_VOLUME_UL: 3.0
  N_TRIALS: 400

mode:
  habituation:
    REWARD_VOLUME_UL: 5.0
    N_TRIALS: 100
  expert:
    REWARD_VOLUME_UL: 2.5
```

Use `msw run ... --task-mode habituation`. The mode name is written back to the subject
YAML so the next session auto-picks it up without the CLI flag.

## Subject YAML structure

```yaml
name: mouse001
project: sleep_lhb
task_overrides:
  sequence:
    start_level: 7
    task_mode: expert
  probabilistic_switching:
    LICK_EVENT_LEFT: Port1In
```

## Setup YAML structure

```yaml
name: setup_a
devices:
  bpod:
    type: bpod
    port_by_path: pci-0000:00:14.0-usb-0:2.1:1.0-port0
  stage:
    type: stage_tower
    port_by_path: pci-0000:00:14.0-usb-0:3:1.0-port0
    axes: ...
    known_positions: ...
calibrations:
  bpod_valve:
    "1":
      updated: "2025-08-07T10:00:00"
      points: [[0.01, 0.7], [0.028, 2.1], ...]
hooks:
  pre_task:
    - mylab.hooks.FetchSubjectLevel
  post_task:
    - mylab.hooks.PushSessionData
```
