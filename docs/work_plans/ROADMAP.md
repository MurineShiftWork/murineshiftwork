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

### FLIR camera subpackage (next larger sprint)

Camera acquisition for the sequence task on Windows 11 acquisition machines.
Sequence task needs **both** RPi cameras (rce, Linux) and FLIR cameras (Bonsai, Win11),
potentially running simultaneously.

Architecture:
- `msw-flir-bonsai` (suite design, partially implemented) → standalone package or
  `hardware/flir/` in current monolith, depending on whether suite migration is ready
- Launch Bonsai as a subprocess from the task; Bonsai runs a workflow that saves video
- Camera start signal: ZMQ message or named-pipe to Bonsai subprocess at trial start
- Camera stop: clean shutdown on session end
- Bonsai workflow file path specified in setup YAML under `flir_camera:` device section
- File naming: `{session_basename}.flir.{camera_id}.{timestamp}.avi` (or `.mp4`)
- Session validation: extend `readers/validate.py` to check FLIR file existence + duration

Key design decisions needed:
1. Whether to use `msw-flir-bonsai`'s existing ZMQ → FastAPI → WebSocket stack, or a simpler
   subprocess-only approach for the Win11 acquisition use case
2. Whether sequence task uses a camera-start/stop softcode signal or the task process manages
   the Bonsai subprocess directly (task-process owned is simpler for the single-machine case)
3. RPI ensemble + FLIR simultaneously: both started at session start, both receive the same
   trial-onset TTL barcode signal for alignment; RCE stays unchanged

### Subject writeback bundle (next sprint after test coverage is clean)

**All three writeback cases now share `save_subject_task_overrides(config_dir, subject, task, overrides)`.**

**1. Sticky named mode** — DONE (2026-05-18)
- When `--task-mode X` is passed, `evaluate_args` writes `{"task_mode": X}` to
  `subject.task_overrides[task]` after the session is set up.
- Next session: if subject YAML has `task_mode` in task_overrides, it is applied as
  a sticky mode (CLI `--task-mode` still wins).
- Mode name is preserved (not expanded params), so subject YAML stays readable.
- Tests: `test_sticky_task_mode_from_subject_yaml_applied`, `test_cli_task_mode_beats_sticky_subject_yaml_mode`,
  `test_subject_yaml_overrides_stack_on_top_of_sticky_mode`

**2. Sequence level progression writeback** — PARTIALLY DONE (2026-05-18)
- `config_dir` is now injected into `settings.task.patched` so tasks can write back state.
- `task_objects.save_session_end()` calls `save_subject_task_overrides(config_dir, subject, "sequence", {"start_level": N})`
  at session end, writing the current level to the git-tracked subject YAML.
- Next session: subject YAML's `start_level` is read as part of `task_overrides["sequence"]`,
  no longer requiring `--task-settings start_level=N`.
- Local `~/.murineshiftwork/sequence/` JSON store kept as secondary store (LabWatch future path).
- **Outstanding**: test for the session-end writeback in an isolated test (needs SimBpod).

**3. Stage position writeback** — DONE (earlier sprint)
- `save_subject_task_overrides` called from `_test_stage_move` with `{"stage_position": name}`.
- Already tested in `test_config_io.py`.

**4. Named modes for all tasks** — NOT YET STARTED
- All task.yaml files already have `mode: {}` structure.
- Content work: define named modes (e.g. habituation, deterministic, probe) in each task.yaml.
- Which tasks need modes: `probabilistic_switching`, `sequence`, `airpuff`, opto tasks.
- `probabilistic_switching_fixedsubjects` already has 5 named modes.

**5. Pre/post hooks — DONE (2026-05-18)**
- `murineshiftwork.logic.hooks` — full implementation; see `docs/concepts/hook_system.md`
- Setup YAML `hooks.pre_task` / `hooks.post_task` and task.yaml `HOOKS_PRE_TASK` / `HOOKS_POST_TASK`
- Wired into `TaskProcess`: pre-hooks after Bpod connects, post-hooks in `__exit__`

### `msw tasks` management CLI (not yet started)

- `msw tasks list` — print all available tasks with one-line description
- `msw tasks defaults <task_name>` — print the bundled `task.yaml` `default:` section
- `msw init task-configs` — copy bundled `task.yaml` files into `<config_dir>/tasks/<name>/task.yaml`
  so the user has a starting point for the config-dir overlay without hand-copying
- Tied to config-dir overlay system; overlay dir already wired in `evaluate_args`

### Pre/post session hook system — DONE (2026-05-18)

- `murineshiftwork.logic.hooks` — `HookContext`, `TaskHook`, `load_hooks()`, `collect_hooks()`,
  `run_pre_hooks()`, `run_post_hooks()`
- `HooksConfig(pre_task, post_task)` added to `SetupConfig` in `config/models.py`
- `TaskProcess.__init__` builds hook context and loads hooks after Bpod connects, before `init_task()`
- `TaskProcess.__exit__` runs post-hooks before `exit_safely()`
- Pre-hooks may mutate `task_settings` (dict is shared by reference); post-hooks may read `output`
- Failures isolated: a raising hook logs WARNING and is skipped; session continues
- 25 tests in `tests/test_hooks.py`: context, base hook, run_pre/post, error isolation, load_hooks, collect_hooks, SetupConfig round-trip

### Docs reorganisation — DONE (2026-05-18)

- Legacy docs moved to `docs/legacy/` (user sorts manually):
  `CLI_REFACTOR_PLAN.md`, `cli_redesign_spec.md`, `FLIR_AND_HOOKS_PLAN.md`,
  `TODO.md`, `CALIBRATION.md`, `calibration/stage.md`, `calibration/visualization.md`,
  `calibration/water.md`, `INSTRUCTIONS_MSW_UPGRADE_20260516.md`
- New docs structure created (skeletons):
  - `docs/concepts/` — architecture, config_system, hook_system, session_files
  - `docs/tutorials/` — calibration, adding_setup, adding_subject
  - `docs/cli/` — run, action, calibration, post, subject, setup, tasks
- `docs/index.md` updated with new section table

### `msw post` scripts — DONE (2026-05-18)

- `msw post clean --data-dir <path> [--event Port4] [--dry-run]` — pure Python CSV cleaner;
  backs up originals, recurses subdirs, dry-run mode
- `msw post run --central-data <path> --provision-scripts <path> [--skip-*] [--dry-run]` —
  thin Python wrapper calling `scripts/run_post_acquisition_tasks.sh`; orchestrates rsync,
  RPi collation, h264 conversion, remote upload via provision_rpi scripts
- Both commands tested in `tests/test_post_and_action.py`

### Opto task consolidation (not yet started — see memory: project_opto_config_design.md)

4 opto tasks (`optotagging`, `optotagging_with_video`, `optotagging_multi_with_video`,
`optotagging_with_power_level`) → 1 unified task with per-protocol stimulation config.

Protocol loop design:
- Each protocol dict: `{n_trials, iti, record_video, laser_power, freq_hz, pulse_width_ms}`
- Execution loop: `video_start (if chosen) → laser loop → video_stop → next protocol / done`
- `laser_power` is per-protocol and fixed for the duration of that protocol (no within-run changes)
- Stimulation config lives in `task.yaml` under a `stimulation:` key (deep-mergeable from overlay)

Stimulation consolidation:
- `optotagging_with_power_level/stimulation.py` → merged into `logic/stimulation.py`
- Both are pypulsepal wrappers; unify into `StimulationController` with `set_power()`,
  `trigger_clock()`, `emergency_off()`; will become `msw-stimulation` in suite split

### Named task config presets — extend to other tasks  ← DONE for fixed-subjects
Named modes (`default:` / `mode:` structure) are live for `probabilistic_switching_fixedsubjects`.
Still to do: propagate the same structure to other tasks that would benefit from named stages
(e.g. `probabilistic_switching`, `sequence_automated`).

### Agent runner / code-level entrypoint (not yet started)

**Design issue:** `evaluate_args` is not a thin CLI adapter — it is the business logic for
building task settings and is tightly coupled to argparse's flat args_dict.  An agent
runner receiving a structured API request (`{"task": "...", "subject": "...", "overrides": {...}}`)
cannot call `evaluate_args` cleanly without constructing a fake CLI dict.

**Planned fix:** extract a standalone pure function:
```python
def build_task_settings(
    task_name: str,
    config_dir: str,
    setup: str = "",
    subject: str = "",
    task_mode: str = "",
    cli_overrides: dict | None = None,
) -> tuple[dict, ExecutionConfig]:
    """Load bundled + overlay configs, apply 5-level priority chain, return patched settings."""
```
- `evaluate_args` calls `build_task_settings` internally — no CLI behaviour changes
- Agent runner also calls `build_task_settings` directly, no fake args_dict needed
- `TaskProcess` already accepts `bpod=` injection and `simulate=` flag — the constructor
  interface is already agent-friendly; only the settings-building seam is missing

**Remaining after `build_task_settings` is extracted:**
- ControllerSession (Phase 2) — owns hardware handles, injects into TaskProcess
- FastAPI `POST /action` — dispatches ActionRequest to ControllerSession
- `msw agent start --setup <name>` → ControllerSession + FastAPI in background

### Simulation mode — DONE (2026-05-16)
- `hardware/bpod/sim.py` — `SimBpod`: logs all SMA and manual_override calls; used by tests
- `logic/scale.py:SimWeighingScale` — deterministic weight for calibration task tests
- `make_scale(scale_type="sim")` factory
- CLI flag `--simulate` wired in parser + TaskProcess: uses SimBpod instead of real hardware

### Hardware action API — Phase 1 DONE, Phase 2 spec below

**Phase 1 (done 2026-05-16)**
- `msw action --setup <name> <device> <action> [key=value ...]`
- `ActionRequest(setup, device, action, params)` Pydantic model in `logic/config/models.py`
- `BpodActionDriver` in `hardware/bpod/actions.py`: `valve_pulse`, `valve_flush`
- Phase 1 is blocking: opens exclusive Bpod connection, runs action, disconnects
- `BpodFactory._write_lock` (threading.Lock) added — not contended in Phase 1, is Phase 2 infrastructure
- CLI warns users not to run while a task session is active

**Phase 2 spec (ControllerSession + in-task override)**

Goal: allow hardware overrides (e.g. manual valve open) during a running state machine,
matching the MATLAB Bpod behaviour where `OverrideSendByte` injects commands mid-trial.

Architecture:
- `ControllerSession` owns all hardware handles (BpodFactory, PulsePal, Stage) for the full
  session lifetime; `TaskProcess` receives them via injection (`bpod=` kwarg already supported)
- Override path uses Bpod firmware's manual override byte protocol (`bpod.manual_override()`),
  which operates at a lower level than the state machine and does not interrupt it
- `BpodFactory._write_lock` gates all serial writes; ControllerSession acquires the lock before
  calling `manual_override()` so the state machine's serial traffic is not interleaved
- FastAPI routes (`POST /action`) dispatch to `ControllerSession.dispatch_action(ActionRequest)`
  using the same `ActionRequest` shape as Phase 1 CLI — no model changes needed
- CLI `msw action` in Phase 2 sends HTTP POST to the running agent instead of opening a
  direct connection (detected by checking for a running agent lock file / port)

Implementation steps (not yet started):
1. `ControllerSession` class in `logic/controller.py` or `hardware/controller.py`
   - `__init__`: open BpodFactory, PulsePal, Stage once
   - `start_task(task_name, settings)` → spawns TaskProcess with injected hardware
   - `stop_task()` → signals TaskProcess, waits, keeps hardware open
   - `dispatch_action(request: ActionRequest)` → acquires _write_lock, calls firmware override
2. FastAPI app in `api/app.py`; `POST /action` calls `session.dispatch_action()`
3. CLI `msw action` auto-detects agent (checks agent socket/port) and switches to HTTP POST
4. Agent startup: `msw agent start --setup <name>` → ControllerSession + FastAPI in background

### ControllerSession / hardware-injection layer
- `TaskProcess` accepts `bpod=` (injected `BpodFactory`) — done
- Next: `ControllerSession` as described in Phase 2 spec above
- Enables: start/stop without reconnecting hardware, multi-task sessions, CLI and web UI
  using the same controller

### Web UI / RPC interface
- Controller exposes `start_task()`, `stop_task()`, `status()` via a thin interface
- CLI, Qt GUI, and web UI all call the same controller
- Follows rpi_camera_ensemble agent pattern

### Test coverage

255 tests pass (2026-05-18).

**Done since last count (2026-05-18):**
- `logic/hooks.py` — 25 tests in `test_hooks.py`: HookContext, TaskHook base, run_pre/post_hooks,
  error isolation, load_hooks by path, collect_hooks from setup config and task settings,
  SetupConfig HooksConfig round-trip

**Previous batch (2026-05-18):**
- `cli/execute.py:run_action` — integration tests: dispatch valve_pulse with SimBpod,
  unknown setup raises, unknown device raises, unsupported device type raises
- `logic/calibration.py:save_calibration_pdfs` — smoke test: PDF created, empty setup
  skipped, single-setup filter works
- `cli/post.py:run_post_clean` — pure Python CSV cleaner: event rows removed,
  dry-run no-op, backup created, recurses subdirs
- `logic/config/io.py:save_subject_task_overrides` — multiple keys, multi-task merge,
  update existing, backward compat via stage_position wrapper
- `cli/evaluate.py` sticky task_mode — subject YAML task_mode applied, CLI mode
  beats sticky, non-mode subject keys stack on top of mode

**Remaining:**
- `hardware/bpod/factory.py` — BpodFactory._write_lock type check; open/close_safely path
- `readers/validate.py:validate_session` — TTL alignment path test
- Namespace reader (`readers/namespace.py`) — smoke test with fixture files

### Namespace package prep / Sprint A (DONE 2026-05-17)

- `murineshiftwork/__init__.py` is now minimal and side-effect-free:
  - `__version__` read from `importlib.metadata.version("murineshiftwork")` — no duplicate string
  - `__author__` only other field
  - No imports of `run_cli`, `read_session_data`, `patch_logging_levels`, `patch_user_settings`
  - No module-level side effects (`patch_logging_levels()` / `patch_user_settings()` removed)
  - Comment block explains namespace package split pattern and version template for subpackages
- `cli/__init__.py:run_cli()` now calls `patch_logging_levels()` + `patch_user_settings()` explicitly at
  CLI startup — the only code path where these side effects are appropriate
- `logic/task_process.py` imports `patch_logging_levels` from canonical source (`logic.log`) not from `__init__`
- Entry point updated: `murineshiftwork.__init__:run_cli` → `murineshiftwork.cli:run_cli`
- Stale `murineshiftwork.egg-info` at repo root removed (was shadowing 1.1.0 with 1.0.0 metadata)
- Version now correct: `murineshiftwork.__version__ == "1.1.0"` confirmed via importlib.metadata
- Namespace subpackage version template documented in `__init__.py`:
  ```python
  from importlib.metadata import version, PackageNotFoundError
  try:
      __version__ = version("msw-namespace")  # pip install name
  except PackageNotFoundError:
      __version__ = "unknown"
  ```

### Session output file consolidation (DONE 2026-05-17)

Single `.msw.session.yaml` replaces three separate files. Version bump 1.0.0 → 1.1.0.

- `{session}.msw.session.yaml` — `msw_format_version: 2`, sections:
  `process:` (msw_version, git_commit, task, subject, setup, serial_port, out_path, session_folder),
  `task_settings:` (patched settings from task_objects), `stage:` (stage config if applicable)
- `TaskProcess.persist_settings()` writes process section at session start (clean fields only,
  no Python types); `update_session_yaml(path, **sections)` utility adds task_settings + stage
  after task init (called from task_objects instead of the old JSON writes)
- `.settings.task.json` writes removed from probabilistic_switching, probabilistic_switching_fixedsubjects,
  sequence_automated task_objects; `stage.save_config()` call removed from fixedsubjects
- `readers/session.py` detects `session.yaml` key from `.msw.session.yaml` filename and
  dispatches to YAML reader; populates settings.process, settings.task, settings.stage;
  old `.json` fallback path kept for backward compat
- `tests/data/fixture_v2/` — minimal v2 session fixture (YAML + jsonl + CSV)
- `tests/test_reader_v2.py` — 14 tests: v2 format parsing, backward compat with fixture_jsonl

### Task cleanup
- `homecage_sleep` — wraps `periodic_trigger_with_video` with fixed params; still present.
  Could be converted to a named mode in `periodic_trigger_with_video/task.yaml` so it's
  accessible via `--task-mode homecage_sleep` without a separate task dir.
  `sleep_with_physiology` already removed. `_test_pyqtgraph_app`, `_test_open_ephys_remote`
  already removed.

### Config: remove configobj — DONE
- `configobj` has no usage in `src/` and is not listed in `pyproject.toml` dependencies.
  The only reference is a comment in `namespace/spec.py` saying it was replaced.

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

## Completed (2026-05-17 / 2026-05-18)

### mypy: tasks.* fully typed (2026-05-18)

- `tasks.*` broad `ignore_errors` override removed from `pyproject.toml`
- All 62 suppressed errors fixed across 12 task files:
  - `TaskRunner.bpod: Any = None` — resolves all `"None" has no attribute …"` cascades in subclasses
  - `TaskRunner.input_kwargs: dict = {}` — always populated from `**kwargs`, never None
  - `TaskProcess.bpod: Any = None`
  - `task_objects.py` files (probabilistic_switching, fixedsubjects, sequence): `bpod: Any`, `task_settings: dict`, `trial_data: list`, `last_outcome: str | None`
  - `online_plotting.py` files: `monitoring_queue: Any`, `kill_queue: Any`, `Queue | None` annotations, `np.ndarray | None`
  - Remaining narrow override: only the two `stimulation.py` pypulsepal wrappers (`logic/stimulation.py`, `optotagging_with_power_level/stimulation.py`) — these will move to `msw-stimulation` in the suite split

### Config-dir task overlay (2026-05-18)

- `<config_dir>/tasks/<task_name>/task.yaml` is deep-merged on top of bundled `task.yaml`
- `deep_merge(base, override)` added to `logic/config/ini.py`: recursive dict merge, lists replaced outright, neither input mutated; re-exported from `logic/config/__init__.py`
- All three existing merge operations in `_build_task_settings_patch` upgraded from `dict.update()` (shallow) to `deep_merge` so nested dicts (e.g. `stimulation:` sub-config) can be partially overridden
- Overlay path stored as `config_file_task_overlay` in args_dict for inspection
- Overlay `mode:` section entries merged into the task mode dict (overlay mode definitions win)
- Full 5-level priority chain: bundled `task.yaml` → config_dir overlay → `--task-mode` → subject YAML `task_overrides` → CLI `-ts`
- **Tests:** 9 unit tests for `deep_merge` in `test_config_io.py`; 6 integration tests for overlay in `test_cli_evaluate.py` covering: override wins, unmentioned keys survive, absent overlay uses bundled only, CLI beats overlay, deep merge of nested keys, full priority chain (all 5 levels)
- **Docs:** `quickstart.md` updated with 5-level chain and overlay workflow; `index.md` feature list updated

### Scripts cleanup (2026-05-18)

- Deleted `scripts/_clean_msw_files.bash`, `_patch_all_setups_config_files.bash`,
  `run_post_acquisition_tasks.bash`, `push_configs_to_setups.sh` (only one rig; push was unused)
- Remaining: `clean_msw_files.sh`, `run_post_acquisition_tasks.sh`
- Roadmap: port remaining scripts to `msw post clean` / `msw post run` Python CLI commands

### `msw tasks` naming decision (2026-05-18)

- `msw tasks` (plural) reserved for task management commands (`msw tasks list`, `msw tasks defaults <name>`, `msw init task-configs`)
- `msw run` remains the execution entry point — avoids confusion between management and execution
- See roadmap items for `msw tasks` implementation

### Subject writeback generalization (2026-05-18)

- `save_subject_task_overrides(config_dir, subject, task, overrides: dict)` added to
  `logic/config/io.py` — generalized version of `save_subject_task_stage_position`;
  merges any dict of keys into `subject.task_overrides[task]`
- `save_subject_task_stage_position` kept as thin wrapper for backward compat
- `config_dir` now injected into `settings.task.patched` so tasks can call writeback functions
- Sticky `task_mode` writeback: when `--task-mode X` is used with a known subject,
  `evaluate_args` writes `{"task_mode": X}` to subject YAML after session setup
- `_build_task_settings_patch` reads `task_mode` from subject YAML task_overrides and
  applies it before other subject override keys; CLI `--task-mode` wins over sticky YAML value
- Sequence `task_objects.save_session_end()` writes `start_level=N` to subject YAML if
  `config_dir` is present in `task_settings` (wired from patched settings)
- 11 new tests for: `save_subject_task_overrides`, sticky mode applied, CLI mode beats sticky,
  subject keys stack on top of mode

---

## Completed (this iteration — 2026-05-15 / 2026-05-16)

### Simulation hardware / virtual Bpod + scale (2026-05-16)
- `hardware/bpod/sim.py` — `SimBpod`: pre-populated 4-port Bpod hardware (max_states=255,
  Valve1-4, PWM1-4, BNC1-2, Tup events); logs all SMA / manual_override calls;
  `run_state_machine` returns True; `hardware` attribute makes `StateMachine(bpod=sim)` work
- `logic/scale.py:SimWeighingScale` — deterministic fixed weight, tare/read tracking
- `make_scale(scale_type="sim")` — factory updated
- Scale injection: both calibration tasks accept `scale=` kwarg; falls back to `make_scale`
  when absent; enables testing without patching
- `tests/test_sim_hardware.py` — 20 tests: SimBpod, SimWeighingScale, make_scale factory,
  BpodActionDriver (dispatch, valve sequence, n_pulses, flush defaults, finally-close)
- `tests/test_calibration_tasks_sim.py` — 6 tests: both calibration tasks smoke-tested
  with sim hardware; verify CSV saved, SMAs fired, scale tared
- `logic/calibration.py:CalibrationDataBase.__add__` — fixed pandas `_append` →
  `pd.concat` (deprecated private API removed in current pandas)
- BpodActionDriver corrected to use `bpod.manual_override()` (firmware byte protocol)
  instead of SMA — SMA is only appropriate for calibration tasks with timed pulse recording

### Hardware action API Phase 1 (2026-05-16)
- `msw action --setup <name> <device> <action> [key=value ...]` CLI subcommand
- `ActionRequest(setup, device, action, params)` Pydantic model in `logic/config/models.py`
- `BpodActionDriver` in `hardware/bpod/actions.py`: `valve_pulse` and `valve_flush` actions
- `BpodFactory._write_lock = threading.Lock()` added to `hardware/bpod/factory.py` — not
  contended in Phase 1 (blocking CLI), is Phase 2 infrastructure for in-task override injection
- Phase 2 spec written to roadmap: ControllerSession owns hardware, FastAPI `POST /action`,
  same ActionRequest shape; `bpod.manual_override()` path gated by `_write_lock`

### Named task config presets / stages (2026-05-16)
- `task.yaml` restructured to `default:` / `mode:` top-level sections for all 11 tasks
- `read_config` returns `raw["default"]` for new format, full dict for legacy flat files
- `read_task_modes` returns `raw.get("mode", {})` for named override sets
- `--task-mode <name>` CLI arg wired through parser → evaluate.py → applied after task defaults,
  before subject YAML overrides and `-ts` CLI overrides (priority chain documented in evaluate.py)
- `probabilistic_switching_fixedsubjects/task.yaml` modes: `stage00habituation` (100/99),
  `stage10deterministic` (100/0), `stage20prob9010` (90/10), `stage30prob905010` (full set), `probe`

### Calibration visualisation CLI (2026-05-16)
- `msw calibration plot [--setup <name>] [--out <dir>]` saves one PDF per setup
- `plot_setup_valve_calibrations()` in `logic/calibration.py`: exponential fit overlaid on scatter,
  one subplot per setup; falls back gracefully when fit fails (e.g. near-linear data)
- `save_calibration_pdfs()`: iterates setup YAMLs, skips those without `bpod_valve` data,
  names files `{setup}--{datetime}.pdf`
- `run_calibration()` in `cli/execute.py`; bypasses `evaluate_args` (no hardware context needed)

### Calibration outlier detection (2026-05-16)
- `flag_outlier_points(times_s, ul_values, sigma_threshold)` in `logic/calibration.py`
- Uses leave-one-out fitting + MAD-based scale to avoid masking (naive global-fit pulls toward outlier)
- Called at end of each valve calibration in `_calibration_liquid_dynamic`; logs warnings per flagged point
- 18 unit tests in `tests/test_calibration_outliers.py`

### Adaptive water-valve calibration protocol (2026-05-16)
- New task: `_calibration_liquid_dynamic` — does not touch `_calibration_liquid_static`
- Adaptive pulse count: `n_pulses = ceil(MIN_SNR × SCALE_NOISE_G × 1000 / expected_µL_per_drop)`,
  clamped to `[MIN_PULSES, MAX_PULSES]`; large drops need far fewer pulses than small ones
- Adaptive time-point grid: initial evenly-spaced grid, then up to `MAX_ADAPTIVE_ROUNDS` rounds
  adding new times at range boundaries and sparse interiors until `[min_ul, max_ul]` is covered
- Tare before each point so sticking from prior measurement doesn't accumulate across points
- Volume estimate for pulse-count planning uses exponential fit when ≥3 points exist, linear fallback
- `_compute_n_pulses`, `_estimate_ul`, `_suggest_additional_times` are pure functions (no hardware)
  with their own unit tests

### Task discovery fix (2026-05-16)
- `list_available_tasks()` now includes `_calibration_*` dirs alongside `_test_*` and normal tasks;
  calibration tasks are now runnable via `msw run -t _calibration_liquid_dynamic`

### Logging: duplicate output root cause fixed (2026-05-16)
- Third-party packages (rpi_camera_ensemble) added `StreamHandler`s to ROOT logger
- `suppress_third_party_console_handlers()` rewrote: tracks MSW-owned handler IDs in
  `_MSW_ROOT_HANDLER_IDS`; removes foreign StreamHandlers from root + all child loggers
  while protecting MSW's own `RichHandler` and `FileHandler`

### Window title metadata fix (2026-05-16)
- `_evaluate_metadata` now always populates `args_dict["metadata"]` from named args
  (`--setup`, `--researcher`, `--experiment`) regardless of whether `--metadata` was passed;
  fixes "n/a" appearing in PyQtGraph window title when `--setup` was provided on CLI

### Test fixes (2026-05-16)
- `validate_config_file_path`: guard against empty-string input (`Path("").exists()` is True)
- `read_config`: returns `{}` for non-YAML files instead of implicit `None`
- Tests updated to use `s_for_ul` / `ul_for_s` API and seconds-based calibration data

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
- `calibrate_water_with_serial_scale` → `_calibration_liquid_static`
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

## Suite Comparison: murineshiftwork vs murineshiftwork_suite (as of 2026-05-17)

Design docs: `/mnt/maindata/code/murineshiftwork_suite/design/`

### Items already done in current monolith (ready to port when suite is active)

| Current package item | Maps to suite component | Status |
|---|---|---|
| `BpodFactory` + `_write_lock` | `msw-tasks/bpod/RobustBpodSession` | Done; port when msw-tasks Phase 3 starts |
| `BpodActionDriver` + `ActionRequest` | `msw-tasks/bpod/` + `msw-server/api/` | Done; ActionRequest shape is final |
| `SimBpod` + `SimWeighingScale` | `msw-tasks/bpod/sim.py` | Done; copy directly |
| `SetupConfig` + `SubjectConfig` Pydantic models | `msw-namespace/config/` | Done; validated in production CLI |
| `logic/io.py` JSONL format + `_NumpyEncoder` | `msw-namespace/io/` or `msw-tasks/io/` | Done; suite data compat contract requires this exact format |
| `logic/barcode.py` + task integration pattern | `msw-tasks` base task mixin | Done in sequence_automated + PS-fixedsubjects |
| `readers/session.py:read_session_data()` | `msw-readers` (future) or keep in legacy | Done; v2 YAML format is the contract |
| `tasks/` namespace (no `__init__.py`) | `msw-tasks` namespace package | Already namespace-compatible |
| `find_task_by_name()` dynamic task loading | `msw-agent` task registry | Done; replace with `@register_task` decorator |
| `TaskProcess` (thread lifecycle, bpod inject) | `msw-agent/TaskProcess` | Done; maps 1:1 to backup agent's process_task.py |
| `update_session_yaml` utility | `msw-namespace/session.py` Session lifecycle | Done; clean hook for session metadata |

### Suite items NOT yet started (sprints to move toward suite)

**Sprint A — Namespace prep in monolith (0.5 day)**
- Verify `src/murineshiftwork/__init__.py` can be made optional without breaking imports
- The monolith *cannot* be a proper namespace package while `__init__.py` exists at root
- Action: document which imports go through `__init__.py` so they can be moved to explicit paths
  before the suite port. (Currently: `run_cli`, `patch_logging_levels`, `patch_user_settings`,
  `read_session_data` — all re-exported. These should be importable from their canonical modules.)

**Sprint B — Port `msw-namespace` (1 day)**
1. Fix `murineshiftwork_suite/msw-namespace/pyproject.toml` from templatepy placeholder
2. Remove `__init__.py` at `murineshiftwork/` root in msw-namespace repo
3. Port: `SetupConfig`, `SubjectConfig` → `msw-namespace/murineshiftwork/namespace/config/`
4. Port: `logic/io.py` JSONL save/load → `msw-namespace/murineshiftwork/namespace/io/`
5. Port: `logic/paths.py` subject name validation → `msw-namespace/murineshiftwork/namespace/paths/`

**Sprint C — Port `msw-tasks` Phase 3 basics (2 days)**
1. Fix `murineshiftwork_suite/msw-tasks/pyproject.toml` from templatepy
2. Remove `__init__.py` at `murineshiftwork/` root in msw-tasks repo
3. Port `BpodFactory` → `msw-tasks/murineshiftwork/tasks/bpod/factory.py`
4. Port `SimBpod` → `msw-tasks/murineshiftwork/tasks/bpod/sim.py`
5. Port `sequence_automated` task as first production task in msw-tasks
6. Add `@register_task` decorator and `task_registry` dict to `msw-tasks`

**Sprint D — Port `msw-agent` Phase 2 basics (2 days)**
1. Fix `murineshiftwork_suite/msw-agent/pyproject.toml` from templatepy
2. Port `backup-msw-repos/murineshiftwork/msw/agent/` → `msw-agent/murineshiftwork/agent/`
   - `MSWProcess`, `TaskProcess`, `LoggerProcess`, `MSWAgent`
3. Wire to task registry from Sprint C: `start_task(task_name)` → dynamic import + run
4. Add `MSWAgent` test: `SimBpod` + `sequence_automated` + in-memory agent lifecycle

**Clean break criteria (from design docs, current status):**
- [ ] msw-agent stable on acquisition hardware
- [ ] msw-tasks: sequence_automated + PS-fixedsubjects + optotagging ported
- [ ] Each ported task barcode-enabled (start/end + relevant TTL)
- [x] msw-namespace: SetupConfig + SubjectConfig ready (done in monolith, just needs porting)
- [ ] Suite sessions readable by existing `read_session_data()` (easy: use same JSONL + `.msw.session.yaml`)
- [ ] msw-server + msw-interface usable (or CLI-only first milestone met)

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
