# MSW Roadmap

Central planning document. Completed work is listed below; git history has the full detail.

---

## Remaining (next sprint)

### highest priority items:
- upgrade for task stage (see docs/roadmap) to move subjects along with default configs. 
  these default configs should live in the task.yaml files
- rename sequence task to only sequence. look at the implementation and 
  whether the task progress of levels is correctly written back to configs / loaded 
  on next session for continuation. this might need to be implemented together with 
  the pre/post hook system (see docs hooks.md)

### Named task config presets (stages / modes) ← NEXT WORK ITEM for fixed task
Each task defines named preset groups in `task.yaml` as top-level keys.
Selecting a preset applies a batch of overrides — no per-param `-ts` juggling.

```yaml
# task.yaml
stage_100_100:
  REWARD_PROB_LEFT: 1.0
  REWARD_PROB_RIGHT: 1.0

stage_90_10:
  REWARD_PROB_LEFT: 0.9
  REWARD_PROB_RIGHT: 0.1
```
CLI: `msw run -t probabilistic_switching -s mouse01 --preset stage_90_10`
Subject YAML can also pin a preset: `task_overrides: {probabilistic_switching: {preset: stage_90_10}}`
Layer: presets apply between task.yaml defaults and subject overrides.

### Simulation mode (virtual hardware)
Dummy classes for Bpod, PulsePal, and Stage that accept all commands and log them instead of
driving hardware. Enables full task dry-runs without any USB devices connected.
- `hardware/bpod/sim.py` — `SimBpod` mirrors `BpodFactory` API; logs all state-machine calls
- `hardware/pulsepal/sim.py` — `SimPulsePal`
- `hardware/stage/sim.py` — `SimStageController`
- CLI flag: `--simulate` (or `--sim`) injects sim objects instead of real hardware
- Simulation output logged at DEBUG level with `[SIM]` prefix

### Hardware action API (valve / LED — for web UI)
Expose discrete one-shot hardware actions callable from CLI or web backend without
running a full task state machine.
- `open_valve(valve_id, duration_ms=25)` / `close_valve(valve_id)` — two-state + timed
- `led_on(port, duration_ms=300)` / `led_off(port)` — two-state + timed
- Defaults: valve 25 ms, LED 300 ms (override via args)
- Tied to `BpodFactory` so the caller owns the connection; web UI backend calls these via RPC

### ControllerSession / hardware-injection layer
- `TaskProcess` accepts `bpod=` (injected `BpodFactory`) — done
- Next: `ControllerSession` that owns all hardware handles (Bpod, PulsePal, Stage) across the
  session and passes them to `TaskProcess`
- Enables: start/stop without reconnecting hardware, multi-task sessions, CLI and web UI
  using the same controller

### Web UI / RPC interface
- Controller exposes `start_task()`, `stop_task()`, `status()` via a thin interface
- CLI, Qt GUI, and web UI all call the same controller
- Follows rpi_camera_ensemble agent pattern

### Task cleanup
- `homecage_sleep` and `sleep_with_physiology` — both wrap `periodic_trigger_with_video` with
  fixed parameters; consolidate once named-preset feature is done
- `_test_pyqtgraph_app`, `_test_open_ephys_remote` — remove or move to `playground/`

### Config: remove configobj
- `configobj` still needed for subject.settings files in external `msw_configs` repo (INI format)
- Migrate `msw_configs/subjects/*.settings` → YAML, then remove configobj dependency entirely

### PS fixed-subjects lick-port mapping
- `task_objects.py` uses `LICK_EVENT_LEFT/RIGHT` keys from task settings (settable per setup)
- Remaining: `LICK_EVENT_CENTER` not yet wired; document keys in task.yaml

### Hardware verification
- Optotagging / airpuff / PS barcode integration: verify on real hardware after PulsePal swap
- `pypulsepal` trigger-channel linking: verify `linkTriggerChannel` param in pypulsepal 0.0.1
  on hardware before first opto session
- sequence_automated piecewise alignment script not yet written

### QueueMonitor Qt decoupling
- `QueueMonitor` in `online_plotting.py` files uses `QtCore.QThread` — GUI only
- Decouple when splitting GUI layer; `TaskRunner` is already plain `threading.Thread`

### File-write audit (MSW output control)
- All session files must be written under `session_folder/` (MSW-managed)
- Current writes: `settings.process.json`, `settings.task.json`, `settings.stage.yaml`, `.df.jsonl`,
  pybpodapi `.csv`/`.json` — all within session_folder ✓
- Exception allowed: `rpi_camera_ensemble` writes its own output files within MSW namespace paths
- Remove: `~/.murineshiftwork/calibration.stage.default.yaml` write-back replaced by setup YAML ✓
- Ongoing: audit any new task added for out-of-namespace writes
- consolidate settings* files to the process and evaluated items into one settings file. 
  this will require a version upgrade for msw with additional reader logic

---

## Completed (this iteration — 2026-05-15 / 2026-05-16)

### Fixed-subjects task: hardware and logging fixes (2026-05-16)
- **BpodFactory softcode proxy**: added explicit `softcode_handler_function` property (getter + setter)
  so pybpodapi's read loop receives the handler — without it, all softcodes were silently dropped
- **Non-blocking stage movement**: moved `move_to_known_position()` calls into a dedicated worker
  thread (`_stage_worker`) fed by a `queue.Queue`; softcode handler now just enqueues the command
  and returns immediately, unblocking pybpodapi's event read loop
- **Valve timer units**: corrected `water_volume_to_valve_time` to return seconds (was returning ms
  due to `s_to_ms=1` bug), matching pybpodapi state timer expectations; fallback `valve_ms_for_ul`
  also fixed with `/1000` conversion
- **Setup YAML `motor_id` → `id`**: five setup YAMLs (setup-1 through setup-4, npx, npxb) had
  `motor_id:` in stage axis definitions; Pydantic model requires `id:` — fixed with sed

### Calibration times in seconds (2026-05-16)
- All `bpod_valve` calibration points in `msw_configs/setups/setup-{1,2,3,4}.yaml` converted from
  milliseconds to seconds (÷1000): e.g. 10 ms → 0.01 s, 82 ms → 0.082 s
- `ValveCalibration.ms_for_ul()` renamed → `s_for_ul()`; `ul_for_ms()` → `ul_for_s()`
- `SetupConfig.valve_ms_for_ul()` renamed → `valve_s_for_ul()`; `valve_ul_for_ms()` → `valve_ul_for_s()`
- `water_volume_to_valve_time()`: removed `s_to_ms` parameter; returns seconds directly
- All three task `task_objects.py` files (probabilistic_switching_fixedsubjects, probabilistic_switching,
  sequence_automated) updated accordingly — no conversion needed anywhere in task code

### Logging cleanup (2026-05-16)
- Removed all `print()` calls from `task_objects.py` (fixed-subjects task); replaced with
  appropriate `logging.info` / `logging.debug` levels
- Trial summary: multiline print → single ~75-char `logging.info` line per trial
- Softcode received, stage queuing, stage back → `logging.debug`; stage at front → `logging.info`
- Block draw internals → `logging.debug`; block switch (probabilities) stays `logging.info`
- Anti-bias and forced-exploration internals → `logging.debug`
- `online_plotting.py`: `print("unknown option")` → `logging.debug`
- `calibration.py` base class: `print()` → `logging.debug`/`logging.info`

### Package structure
- Namespace package: `tasks/` has no `__init__.py`; filesystem scan replaces `pkgutil.iter_modules`
- `hardware/bpod/` subpackage: `BpodFactory` (renamed from `RobustBpodSession`), `ttl.py`, `water.py`
- `user_settings.py` / `user_settings_8port.py` moved from `settings/` → `hardware/bpod/`
- `settings/` package removed entirely; `machine_config.py` fallback chain ends at historical default
- `logic/specific_state_machines.py` deleted; TTL functions → `hardware/bpod/ttl.py`, water → `hardware/bpod/water.py`
- `hardware/pulsepal/` stub deleted (empty, no references)
- `io/` backward-compat shim deleted; canonical path is `logic/io.py`
- `external/` package deleted; `logic/gui.py` deleted; `logic/pybpod_helpers.py` deleted
- `logic/config/` subpackage: `ini.py`, `io.py`, `models.py`; old flat files removed

### CLI
- `cli/defaults.py`, `cli/preflight.py` factored out of evaluate.py
- Settings patch priority (lowest → highest): task.yaml defaults → SubjectConfig.task_overrides → CLI `-ts`
- Subject registration: YAML per-subject files in `msw_configs/subjects/`; `subject.settings` INI no longer read
- `run_register()` rewritten to write/delete/rename YAML files
- `msw subject add/list`, `msw setup create/list`, `msw init` subcommands added
- Pre-flight hardware check fires before any session files are created
- Stage auto-move: `_apply_stage_position()` reads `stage_position` from patched settings, moves stage before task starts

### Task settings migration
- All `task.settings` INI files converted to `task.yaml` (YAML, `yaml.safe_load`)
- `read_config` detects `.yaml`/`.yml` by extension; falls back to ConfigObj for INI (external files)
- Parser default: `task.settings` → `task.yaml`

### Task naming
- `calibrate_stage_tower` → `stage_move` → deleted; `_test_stage_move` is canonical
- `_test_stage_tower` → `_test_stage_move`
- `calibrate_water_with_serial_scale` → `_calibration_water_with_serial_scale`
- Convention: normal tasks (no underscore prefix), `_test_*`, `_calibration_*`

### Stage writeback
- `_test_stage_move` (formerly `stage_move`): saves axis limits and known_positions back to setup YAML
  via `update_stage_config(config_dir, setup_name, ctrl.config)` in `logic/config/io.py`
- `space` key prints full live config (YAML-formatted, positions refreshed from hardware)
- Setup YAML is always authoritative for axis limits — calibration file no longer overrides it
- `save_subject_task_stage_position(config_dir, subject, task, position_name)` writes `stage_position`
  into `SubjectConfig.task_overrides[task]`; pre-task auto-move reads it back
- Calibration mode: `--task-settings calibrate=true` expands limits to 1–999 for free movement;
  use u/i/o / j/k/l to set new limits, enter saves them to setup YAML

### Task naming (finalised 2026-05-16)
- `stage_move` deleted — `_test_stage_move` is the canonical keyboard-driven stage tool
- `_test_stage_move` now has full feature set: set limits, known positions, config dump, write-back

### Stage config priority
- `evaluate.py`: setup YAML stage device always wins over any saved calibration file
  (old `cal_has_axes` gate that let stale calibration files shadow setup config removed)

### Subject config models
- `SubjectConfig` Pydantic model; `load_subject_config` / `save_subject_task_stage_position` in `logic/config/io.py`
- `SetupConfig`: bpod port resolution, camera config path, `device_port()` method
- `ExecutionConfig`: wires setup + subject + task settings for downstream use

### Hardware
- `BpodFactory`: auto 4/8-port detection; `bpod=` injection into `TaskProcess` for controller layer
- `TaskRunner`: plain `threading.Thread` (was `QtCore.QThread`); no Qt dependency in logic layer
- `logic/stimulation.py` and `optotagging_with_power_level/stimulation.py`: rewritten to use `pypulsepal.PulsePal`

### Flush water
- `_test_flush_water`: added `FLUSH_VALVES_SEQUENTIALLY` — when true, cycles through each valve
  individually (one state machine per valve) rather than opening all at once; `task.yaml` added

### Readers and tests
- `readers/validate.py`: `validate_session()` with three-tier check (MSW completeness, RCE, TTL alignment)
- Test fixtures: `tests/data/fixture_jsonl/` (3-trial JSONL session), `tests/data/fixture_pkl/` (pkl child session)
- **134 tests passing**

---

## Architecture reference

Current package layout:
```
murineshiftwork/
  cli/           __init__, defaults, evaluate, execute, parser, preflight
  hardware/      bpod/ (BpodFactory, factory, patch_user_settings, user_settings,
                        user_settings_8port, ttl, water)
  logic/         barcode, calibration, config/ (ini/io/models), io, log,
                 machine_config, maths, misc, paths, sounds,
                 stimulation, task_process
  namespace/     spec (namespace session builder)
  readers/       session, files, namespace, alignment, validate
  tasks/         (namespace package — each task is murineshiftwork.tasks.<name>)
                 naming: normal tasks (no underscore), _test_*, _calibration_*
                 config: task.yaml (YAML)
```

Planned split (murineshiftwork_suite):
- `murineshiftwork` — core: cli, logic, namespace, readers, settings + all tasks except sequence
- `murineshiftwork_task_sequence` — contributes `murineshiftwork.tasks.sequence_automated` via namespace
- Each moves to own repo under `murineshiftwork_suite/` monorepo layout
