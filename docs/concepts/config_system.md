# Configuration System

## Config layers

Settings are resolved from multiple sources in priority order (lowest → highest):

1. **Bundled `task.yaml` defaults** — shipped with each task package
2. **Config-dir overlay** — `<config_dir>/tasks/<task>/task.yaml` deep-merges on top
3. **Task mode** — named block from `task.yaml mode:` section (sticky via subject YAML or `--task-mode`)
4. **Subject YAML `task_overrides`** — per-subject, per-task overrides
5. **CLI `-ts KEY=VALUE`** — highest priority, one-off overrides

## Inspecting task defaults and modes

Before writing an overlay, inspect the bundled defaults:

```bash
# Print all keys and their defaults for a task
msw tasks defaults _test_flush_valves

# List the named modes and which keys they override
msw tasks modes _test_flush_valves
```

## Config-dir overlay example

To override a task's bundled defaults for a specific rig, create a `task.yaml` in the
config-dir tree.  Keys absent from the overlay are inherited from the bundled file.

For example, to change the default valve list and flush time for `_test_flush_valves`:

```
/mnt/maindata/msw_configs/tasks/_test_flush_valves/task.yaml
```

```yaml
default:
  VALVE_NUMBERS: [1, 3]         # only flush reward valves on this rig
  VALVE_OPENING_TIME_MS: 60.0   # override bundled default of 50 ms

mode:
  wash:
    VALVE_OPENING_TIME_MS: 1500.0  # shorter wash on this rig
```

Copy the bundled file as a starting point:

```bash
msw tasks init-configs _test_flush_valves
```

Then edit `<config_dir>/tasks/_test_flush_valves/task.yaml`.

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

---

## Config schema upgrade

When the bundled `task.yaml` (or setup/subject schema) gains new fields, the
locally stored overlay in `msw_configs/` does not automatically pick them up
— the overlay only stores intentional user deviations from bundled defaults.

### On-load behaviour

When MSW loads a config file whose `msw_schema_version` is behind the bundled
version, it emits a one-time console warning:

```
WARNING  Config 'tasks/sequence/task.yaml' is at schema v2, bundled is v3.
         Run `msw config upgrade task sequence` to add new defaults.
```

MSW **never writes to config files on load**. The warning is informational
only; the session starts with the current resolved settings, which already
include new-field defaults from the bundled file via `deep_merge`.

### Upgrade command

```bash
msw config upgrade task sequence        # task overlay
msw config upgrade setup setup-npxb    # setup YAML
msw config upgrade subject mouse001    # subject YAML

msw config upgrade --all               # all configs in config-dir

# Preview without writing
msw config upgrade task sequence --dry-run
```

The command:
1. Shows a diff of keys that would be added (new bundled defaults absent from
   the overlay file).
2. Asks for confirmation unless `--yes` is passed.
3. Writes **only** new keys (with their bundled default values) to the overlay.
   Existing user values are never touched.
4. Bumps `msw_schema_version` in the overlay file.

### Guards

- `--dry-run` always available; shows the diff without writing.
- `--yes` for scripted / post-install use.
- Values already present in the overlay are never overwritten regardless of
  flags — there is no `--force-overwrite`.
- The command writes a `.bak` file alongside the original before modifying.

### Schema version field

Each config type carries `msw_schema_version: N` (integer, top-level for
setup and subject YAMLs; inside `default:` for task overlays). The bundled
file is the authority on the current version. Overlays missing the field are
treated as version 0.
