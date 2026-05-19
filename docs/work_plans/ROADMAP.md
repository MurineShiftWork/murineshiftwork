# Roadmap

Revolving TODO list. Completed items move to DONE with `· date · short-hash`.
Design details live in memory files or separate docs — not here.

---

## Manual (requires human action)

- [ ] **PyPI: publish deprecation stub** — `serial-weighing-scale 3.0.0` at `/mnt/maindata/code/serial_weighing_scale_stub/`
  ```
  cd /mnt/maindata/code/serial_weighing_scale_stub
  python -m build && twine upload dist/*
  ```
- [ ] **GitHub: create repo `serial-scale-hx711`** then push `external/serial_scale_hx711` (remote already set to `https://github.com/larsrollik/serial-scale-hx711.git`)
- [ ] **GitHub: create repo `serial-scale-bench`** then push `external/serial_scale_bench` (remote already set to `https://github.com/larsrollik/serial-scale-bench.git`)

---

## TODO

- [ ] ControllerSession / setup-agent architecture — see ROADMAP Notes for design sketch
- [ ] `msw_flir_bonsai.timestamps` — finish user's existing unwrap code (FlyCapture 128s cycle), wire into `preprocess_camera_csv`; user has existing implementation to integrate
- [ ] setup-agent + central server + Vue/TS frontend — see `docs/work_plans/DRAFT_agent_architecture.md`

---

## DONE

- [x] msw-flir-bonsai package — BonsaiCameraRunner, MultiCameraRunner, timestamp unwrapping, barcode+TTL alignment; 9 tests; Bonsai workflows for FlyCapture/Spinnaker 1-cam/2-cam · 2026-05-18 · cbc3981 (external/)
- [x] fill docs — cli/tasks.md, concepts/architecture.md stub removed · 2026-05-18 · pending
- [x] opto task consolidation — 4 tasks → 1 unified `optotagging`; multi-protocol loop, stimulation_defaults, laser_power merged into logic/stimulation.py · 2026-05-18 · d7d3068
- [x] `msw tasks` CLI — `list`, `defaults <name>`, `init task-configs`, `modes <name>` · 2026-05-18 · a2b859b
- [x] named modes content — habituation/expert/probe defined in `probabilistic_switching`, `sequence`, `airpuff` task.yaml · 2026-05-18 · a2b859b
- [x] `build_task_settings()` extraction — `logic/task_settings.py`, decouples evaluate_args from argparse flat dict · 2026-05-18 · a2b859b
- [x] scale device config — `ScaleDevice` model, setup YAMLs updated, scale_type/baudrate wired through evaluate.py · 2026-05-18 · 1aa4ce8
- [x] serial-scale-hx711 + serial-scale-bench packages — formalized with hatchling/cz/pre-commit/GH Actions; BenchScaleAdapter added · 2026-05-18 · 73a9861
- [x] sequence level writeback integration test (5 tests, test_sequence_writeback.py) · 2026-05-18 · dc9b438
- [x] `TaskProcess.__del__` removed — redundant with `__exit__`, hazardous at shutdown · 2026-05-18 · dc9b438
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

**Machine-local config (`~/.murineshiftwork/msw_machine.yaml`):** This file tells MSW where to find the shared config directory. Priority chain for `config_dir` (highest wins): (1) `--config-dir` CLI arg, (2) `MSW_CONFIG_DIR` env var, (3) `config_dir` key in `~/.murineshiftwork/msw_machine.yaml`, (4) `/mnt/maindata/msw_configs` (historical default). The current live config directory on this machine is `/mnt/maindata/msw_configs` — subjects under `subjects/`, setups under `setups/`. Set a different machine with `msw config set-dir <path>` or edit the YAML directly. Full logic in `src/murineshiftwork/logic/machine_config.py`.

**ControllerSession / setup-agent architecture (design 2026-05-18):**
Three-layer target: **Web UI** (HTMX + Jinja2, no React build step) ↔ **Central server** (thin FastAPI proxy + registry) ↔ **Setup-agents** (one long-lived FastAPI per rig, port 8765). CLI: `msw run` checks `MSW_AGENT_URL` / probes `localhost:8765` then dispatches `SessionStartRequest` via HTTP; falls back to direct execution if no agent reachable (`--no-agent` flag always bypasses). Setup-agent endpoints: `/hardware/{status,connect,disconnect,action}`, `/session/{status,start,stop,events (WS)}`, `/config/{subjects,tasks,setup}`. **Hardware lifetime**: Bpod stays connected across sessions — inject `bpod=` into `TaskProcess` (same as existing injection pattern); close only on `/hardware/disconnect` or fatal serial error. **Sandboxing**: existing `TaskRunner(Thread)` is sufficient; agent wraps `TaskProcess` in `try/except BaseException` and transitions state to `"error"`. **Discovery**: heartbeat registration (agents POST to `MSW_CENTRAL_URL` every 30 s; entries >90 s old marked offline) — no mDNS. **Auth**: HTTP Basic, `MSW_AGENT_PASSWORD` env var per rig; nginx TLS terminator if exposed beyond LAN. **Session replay**: read `.msw.session.yaml` files from shared data dir after the fact — no DB. **Trial event WS schema**: `{event, rig_name, trial_index, timestamp, reward_count, extra: {}}`. **New modules**: `src/murineshiftwork/agent/` (app.py, hardware_manager.py, session_manager.py, routers/) + `src/murineshiftwork/central/` (app.py, registry.py, proxy.py) + new Pydantic models: `SessionStartRequest`, `SessionStatus`, `TrialEvent`. New parser subcommand: `msw agent {start,stop,status}`. **v1 non-scope**: no DB, no mDNS, no live plots in web UI, no Windows agent, no multi-rig sync.

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
