# Refactoring Report

*Generated 2026-06-02. Agent review of `src/murineshiftwork/` for code debt, coupling, and clarity.*
*Scope: `logic/`, `hardware/`, `namespace/`, `readers/`, `logagent/`, `hooks/`, `tasks/sequence/`, `tasks/calibration/`, `tasks/optotagging/`.*
*This is not a bug report — all findings are structural or organisational.*

---

## A. Module organisation / `__init__.py` content

**`hooks/__init__.py:1`** — All hook logic (data types + execution engine) in one `__init__.py`. → Split into `hooks/types.py` (`SessionAbortError`, `HookContext`, `TaskHook`) and `hooks/runner.py` (`load_hooks`, `collect_hooks`, `run_pre_hooks`, `run_post_hooks`); `__init__.py` re-exports only.

**`logic/paths.py:1`** — Pure re-export shim for `namespace.paths` with unrelated helpers (`get_host_ip`, `get_host_name`, `test_path_is_writable`) mixed in. → Move utilities to `logic/misc.py`; eliminate the shim once callers import from `namespace.paths` directly.

**`namespace/__init__.py:6`** — `build_data_paths` re-exported here and again via `logic/paths.py` — two indirection layers for a deprecated shim. → Remove from `namespace/__init__.py`.

**`namespace/__init__.py:12`** — `NamespaceLevelSpec` and `NamespaceSpec` re-exported but no production code imports them from `murineshiftwork.namespace`. → Drop; callers should import from `acquisition_namespace` directly.

**`logagent/__init__.py:1`** — Empty, so callers must use `logagent.logagent.LogAgent`. → Add re-exports for `LogAgent` and `create_app`.

**`hardware/bpod/__init__.py:18`** — `patch_user_settings()` defined inline in `__init__.py` with runtime side-effects and a lazy `confapp` import. → Move to `hardware/bpod/factory.py` or `hardware/bpod/settings.py`.

---

## B. Cross-package coupling

**`logic/task_process.py:16`** — `logic/` imports `BpodFactory` from `hardware/` at module level — wrong layer direction (`logic` should not construct hardware objects). → Pass a pre-built bpod instance from the CLI layer.

**`logic/task_process.py:342`** — Deferred import of `LogAgent` from `logagent/` (guarded by `try/ImportError`). Architecture is inverted: `logic` should not know about the monitoring subsystem even optionally. → Accept an optional relay queue/factory as a constructor parameter.

**`logic/misc.py:42`** — `list_available_tasks()` imports `murineshiftwork.tasks` at call time — `logic/` reaching into `tasks/`. → Move to `cli/tasks.py`; only called from CLI code.

**`hardware/camera/client.py:31`** — Deferred imports of `logic.config.models.CameraConfig` and `logic.log.*` — hardware importing from logic. → Accept `CameraConfig` as a typed parameter; move the log helper to a neutral utility module.

**`tasks/_test_video/_test_video.py:11`** — Imports `OnlinePlottingForPS` from `probabilistic_switching` — a test task depending on a production task's internal class. → Remove; `_test_video` does not need a real plot renderer.

**`tasks/_test_trigger_with_video/...:1`** — Entire file is a single re-import of `periodic_trigger_with_video.run_task`. → Delete; run the base task via CLI flags.

**`tasks/openfield/openfield.py:1`** and **`tasks/sleep_homecage/...:1`** — Single-line re-import wrappers for `periodic_trigger_with_video`. → Either delete and map names in the CLI task registry, or extract a shared base module all three import from.

**`tasks/sequence/task_objects.py:177`** — Deferred import of `update_session_yaml` from `logic.task_process` inside a task. → Move `update_session_yaml` to `logic/io.py` or `namespace/msw_files.py`.

**`tasks/optotagging/optotagging.py:16`** — Imports `deep_merge` from `logic.config.ini` directly, bypassing the package's public API. → `from murineshiftwork.logic.config import deep_merge`.

---

## C. God objects / oversized files

**`tasks/sequence/task_objects.py:1`** — 874 lines: level loading, subject registry, valve calibration, SMA construction, two scoring algorithms, reward perturbation, level advancement, JSONL saving. → Split into `state_machine.py` (SMA construction) and `scoring.py` (`_score_sequence_*`, `_update_level`); move `RewardPerturbation` to `logic/perturbation.py`.

**`tasks/probabilistic_switching_fixedsubjects/task_objects.py:1`** — 897 lines, same multi-responsibility pattern. → Split: block/probability logic, stage management, and SMA construction are distinct concerns.

**`logic/calibration.py:1`** — 608 lines mixing data model, statistical fitting, and visualisation. → Split into `calibration/data.py`, `calibration/stats.py`, `calibration/viz.py`.

**`hardware/stimulation.py:1`** — 507 lines mixing waveform math with stateful hardware wrapper. → Move `generate_waveform_voltages`, `_ramp_envelope`, `power_to_voltage` to `hardware/stimulation_math.py` or `logic/waveform.py`.

**`logic/task_process.py:1`** — 482 lines: `TaskProcess`, `TaskRunner`, `update_session_yaml` (free function), `ExampleTask` (scaffold). → Move `update_session_yaml` to `logic/io.py`; delete or relocate `ExampleTask`.

---

## D. Inline logic that belongs elsewhere

**`tasks/sequence/task_objects.py:824`** — `_update_level`/`_advance_level`/`_regress_level` mutate task state directly. → Extract to a pure function `compute_level_update(...) -> int` in `logic/`.

**`tasks/sequence/task_objects.py:747`** — Reward accounting inlined in `update()`. → Extract `_compute_trial_rewards(states, sequence, effective_rewards)`.

**`tasks/sequence/sequence.py:94`** — ~40 lines of stop-criterion logic with `_warned_stop` state inside the trial loop. → Move to a `StopCriteria` dataclass in `logic/` with a `check(info) -> list[str]` method.

**`tasks/optotagging/optotagging.py:27`** — `OptoTaggingRecord.__init__` constructs subprotocol directory paths by string-slicing `session_file_path`. → Use `msw_file()` or a `subprotocol_dir()` helper in `namespace/manifest.py`.

**`hardware/stimulation.py:468`** — `_check_channels_active_reset` never called by any code path. → Delete.

---

## E. Naming and clarity

**`logic/task_process.py:125`** — `ExampleTask` development scaffold in a production module. → Delete or move to `tasks/_example/`.

**`hardware/stimulation.py:130`** — `test = 0` class attribute shadows pytest discovery and is type-ambiguous. → Rename to `_simulation_mode: bool = False`.

**`hardware/stimulation.py:107`** — Mutable class-level arrays on `Stimulation` create shared-state bugs when more than one instance exists in a process. → Move all mutable state to `__init__`.

**`hardware/bpod/factory.py:91`** — `_MACHINE_NAMES` dict recreated inside the retry loop body on every iteration. → Hoist to module-level constant.

**`hardware/bpod/ttl.py:12`** — `output_chanel_pulse` parameter name typo throughout (missing `n`). → Rename to `output_channel_pulse`.

**`logic/config/models.py:181`** — `ValveCalibration.validate()` shadows Pydantic's `validate` classmethod with `# type: ignore[override]`. → Rename to `check_quality()`.

**`hardware/stimulation.py:493`** — `Stimulation` has `__exit__` but no `__enter__`, so it cannot be used as a context manager. → Add `__enter__(self) -> "Stimulation": return self`.

**`logic/calibration.py:33`** — `CalibrationData.__add__` mutates `self` in place and returns `self` — violates `+` semantics. → Rename to `add_point()`.

**`readers/__init__.py:1`** — Six separate `from X import Y as Y` blocks for five symbols. → Consolidate with `__all__`.

---

## F. Dead code

**`logic/calibration.py:312`** — `fit_calibration_exp`, `evaluate_calibration_curve_continuous`, `evaluate_calibration_curve_y_to_x` have no callers. → Delete all three.

**`logic/calibration.py:608`** — `CalibrationDataWater = CalibrationDataLiquid` back-compat alias; calibration tasks could just import `CalibrationDataLiquid`. → Update tasks, delete alias.

**`logic/log.py:20`** — `get_default_log_file_path` — no callers, marked for deletion in legacy plan. → Delete.

**`logic/log.py:132`** — `write_json` — no callers; serialisation is handled by `logic/io.py`. → Delete.

**`logic/misc.py:8`** — `unpack_input_dict` and `list_submodules` — no callers. → Delete both.

**`logic/calibration.py:49`** — `CalibrationData.make_output_dir` never called. → Delete.

**`logic/calibration.py:313`** — Commented-out numpy example code inside a production function body. → Delete.

**`tasks/sequence/task_objects.py:208`** — `_fetch_subject_state` is half-dead: `_load_level` explicitly ignores its return value. → If JSON store is write-only (crash recovery), remove the read path from `_load_level` and document that `_fetch_subject_state` is used only by `save_session_end`.

**`logic/misc.py:114`** — `draw_jittered_trial_time(poisson=True)` raises `NotImplementedError`. → Remove the `poisson` parameter until implemented.

**`readers/session.py:205`** — `if __name__ == "__main__":` block with hardcoded paths that no longer exist. → Delete.

**`hardware/bpod/ttl.py:94`** — `# FIXME: upstream` comment with no context. → Resolve or delete.
