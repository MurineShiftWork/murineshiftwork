# MSW Roadmap

Central planning document. Active items only; completed work is in git history and session memory.

---

## In progress / next sprint

### Named task config presets (stages / modes)
Each task can define named preset groups in its `task.settings` (or a sidecar YAML).
Selecting a preset by name applies a batch of overrides — no per-param `-ts` juggling.

Proposed design:
```ini
# task.settings
[stage_100_100]
REWARD_PROB_LEFT = 1.0
REWARD_PROB_RIGHT = 1.0

[stage_90_10]
REWARD_PROB_LEFT = 0.9
REWARD_PROB_RIGHT = 0.1
```
CLI: `msw run -t probabilistic_switching -s mouse01 --stage stage_90_10`
Subject YAML can also pin a preset: `task_overrides: {probabilistic_switching: {stage: stage_90_10}}`

Layer in the existing settings patch priority: presets apply between INI defaults and subject overrides.

### Controller / hardware-injection layer
- `TaskProcess` now accepts `bpod=` (injected `RobustBpodSession`) — done
- Next: `ControllerSession` that owns all hardware handles (Bpod, PulsePal, Stage) across the
  session and passes them to `TaskProcess`
- Enables: start/stop without reconnecting hardware, multi-task sessions, CLI and web UI
  using the same controller

### Web UI / RPC interface
- Controller exposes `start_task()`, `stop_task()`, `status()` via a thin interface
- CLI, Qt GUI, and web UI all call the same controller
- Follows rpi_camera_ensemble agent pattern

---

## Pending items

### Task cleanup
- `_calibration_stage_tower` (done: was `calibrate_stage_tower`) — possibly further rename
  to `_calibration_stage_move` to clarify it does not run bpod acquisition; `_test_stage_tower`
  would follow accordingly
- `homecage_sleep` and `sleep_with_physiology` — both wrap `periodic_trigger_with_video` with
  fixed parameters; consolidate once named-preset feature is done
- `_test_pyqtgraph_app`, `_test_open_ephys_remote` — remove or move to playground/

### Config migration
- Remove `configobj` dependency; migrate task.settings INI files → YAML with same key names
- `logic/config/ini.py` is the isolation boundary — only that file needs changing

### Hook system
- Design: `docs/work_plans/HOOKS.md`
- Implementation: `logic/hooks.py` — not yet started
- Pre/post-trial hooks for conditional logic without task code changes

### PS fixed-subjects lick-port mapping
- `probabilistic_switching_fixedsubjects/task_objects.py` still has hardcoded Port1/2/3In
- Apply same HARDWARE_PORT_LEFT/CENTER/RIGHT pattern as PS main task

### Hardware
- Optotagging / airpuff / PS barcode integration: verify on real hardware after PulsePal swap
- `pypulsepal` trigger-channel linking: the `linkTriggerChannel{N}` param may not be in
  pypulsepal 0.0.1's `PARAM_DTYPE_MODEL_*` lookup; verify on hardware before first opto session

### Readers
- Validate legacy pkl reader against actual pkl session once one is available
- `readers/validate.py` — 0% test coverage; add validation tests

### QueueMonitor Qt decoupling
- `QueueMonitor` in `online_plotting.py` files uses `QtCore.QThread` — GUI only
- Decouple when splitting GUI layer; `TaskRunner` is already plain `threading.Thread`

---

## Architecture reference

Current package layout (post-refactor):
```
murineshiftwork/
  cli/           __init__, defaults, evaluate, execute, parser, preflight
  hardware/      bpod/ (BpodFactory, patch_user_settings, user_settings,
                        user_settings_8port, ttl, water), pulsepal/
  logic/         barcode, calibration, config/ (ini/io/models), io, log,
                 machine_config, maths, misc, paths, sounds,
                 stimulation, task_process
  namespace/     spec (namespace session builder)
  readers/       session, files, namespace, alignment, validate
  settings/      default calibration files only (pure data package)
  tasks/         (namespace package — each task is murineshiftwork.tasks.<name>)
                 naming: normal tasks (no underscore), _test_*, _calibration_*
```

Planned split (murineshiftwork_suite):
- `murineshiftwork` — core: cli, logic, namespace, readers, settings + all tasks except sequence
- `murineshiftwork_task_sequence` — contributes `murineshiftwork.tasks.sequence_automated` via namespace
- Each moves to own repo under `murineshiftwork_suite/` monorepo layout
