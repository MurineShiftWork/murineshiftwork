# Roadmap

Revolving TODO list. Completed items move to DONE with `· date · short-hash`.
Design details live in memory files or separate docs — not here.

---

## TODO

- [ ] opto task consolidation — 4 tasks → 1 unified `optotagging`; design locked in memory/project_opto_config_design.md
- [ ] opto task consolidation — 4 tasks → 1 unified `optotagging`; design locked in memory/project_opto_config_design.md
- [ ] `msw tasks` CLI — `list`, `defaults <name>`, `init task-configs`

- [ ] named modes content — define habituation/expert/probe modes in `probabilistic_switching`, `sequence`, `airpuff` task.yaml
- [ ] `build_task_settings()` extraction — standalone fn for agent runner; decouples evaluate_args from argparse flat dict
- [ ] fill docs skeleton pages — `docs/concepts/`, `docs/tutorials/`, `docs/cli/`
- [ ] FLIR camera subpackage — Win11 Bonsai subprocess; design in memory/project_flir_bonsai.md
- [ ] ControllerSession (Phase 2) — owns hardware handles, injects into TaskProcess; enables concurrent action + task

---

## DONE

- [x] sequence level writeback integration test (5 tests, test_sequence_writeback.py) · 2026-05-18 · pending
- [x] `TaskProcess.__del__` removed — redundant with `__exit__`, hazardous at shutdown · 2026-05-18 · pending
- [x] auto-bump workflow (bump.yaml, tag_only=true in cz) · 2026-05-18 · 1777835
- [x] code review prompts doc; cz bump fix · 2026-05-18 · 6131087
- [x] hook system — HookContext, TaskHook(fatal=), SessionAbortError, collect/load/run, 34 tests · 2026-05-18 · 0d32b4a
- [x] subject writeback — save_subject_task_overrides, sticky task_mode, config_dir inject · 2026-05-18 · 0d32b4a
- [x] sequence level writeback — save_session_end() writes start_level to subject YAML · 2026-05-18 · 0d32b4a
- [x] msw post clean + run commands (13 tests) · 2026-05-18 · 0d32b4a
- [x] docs reorganisation — legacy/, concepts/, tutorials/, cli/ skeletons · 2026-05-18 · 0d32b4a
- [x] 5-level settings priority chain — bundled → overlay → sticky mode → subject keys → CLI · 0d32b4a
- [x] config-dir overlay — deep-merge user task.yaml on top of bundled defaults · 0d32b4a
- [x] named task modes (default:/mode: structure) — all task.yaml files; fixedsubjects has 5 modes · 31eba57
- [x] namespace package prep — tasks/__init__.py removed, murineshiftwork/__init__.py minimal · 671ac4d
- [x] session output consolidation — single .msw.session.yaml (format v2), version 2.0.0 → 2.1.0 · 671ac4d
- [x] simulation mode — SimBpod, SimWeighingScale, --simulate flag · 75f7916
- [x] hardware action API Phase 1 — msw action, BpodActionDriver, ActionRequest · 75f7916
- [x] mypy tasks.* types cleared · 39f23da
- [x] QThread → threading.Thread in TaskRunner · 54e855c
- [x] CLI restructure — defaults.py, preflight.py, evaluate.py split · 1092f37
- [x] logic/config subpackage — models.py, io.py, ini.py · 1092f37
- [x] hardware/bpod/ subpackage — BpodFactory, ttl.py, water.py, user_settings · 1092f37
- [x] task settings INI → YAML migration (all task.yaml files) · d8d48ce
- [x] configobj removed from dependencies · d7fc13e
- [x] io/ package removed; logic/io.py canonical · 1092f37
- [x] PulsePal → pypulsepal rewrite · 1092f37
- [x] stage movement rename (_calibration_stage_tower → _test_stage_move) · 1092f37
- [x] reader validation tests + fixture files · 75f7916

---

## Notes

**`TaskProcess.__del__` hazard:** `__del__` calls `exit_safely()` which does serial I/O.
At interpreter shutdown module globals may be `None`, making `self.bpod.close_safely()` raise.
`__exit__` already guarantees cleanup for all `with TaskProcess(...)` usage (every task).
Fix: remove `__del__` entirely.

**`build_task_settings()` design:** extract the 5-level priority chain from `evaluate_args`
into a pure function `build_task_settings(task_name, config_dir, setup, subject, task_mode, cli_overrides) → (dict, ExecutionConfig)`.
`evaluate_args` calls it; agent runner calls it directly without constructing a fake CLI dict.

**ControllerSession (Phase 2):** owns Bpod/Stage/PulsePal handles for the full session lifetime.
`TaskProcess` receives them via `bpod=` injection (already supported). FastAPI `POST /action`
dispatches to ControllerSession. `msw agent start --setup <name>` starts it in background.
