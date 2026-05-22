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

- [ ] **`hardware/bpod/device.py`** — `BpodDevice(DeviceProtocol)` wrapping `BpodFactory`; wire `HardwareManager` into `execute.py`; see `MASTER_PLAN.md §3`
- [ ] **Bpod retry — hardware verification** — test fixed retry on device `pci-0000:00:14.0-usb-0:4:1.0 → ttyACM7`; confirm 3-attempt / 2s-sleep resolves first-connect failures
- [ ] **MSW Monitor — Step 1: server + relay** — `monitor/relay.py` (`TrialRelay` daemon Process), `monitor/server.py` (FastAPI, in-memory SessionState, PlotSpec computation); see `MASTER_PLAN.md §5`
- [ ] **MSW Monitor — Step 2: TaskProcess wiring** — read `monitor_url` from machine config, start `TrialRelay`, add `put_nowait()` after `save_trial_data()` in `sequence`, `probabilistic_switching_fixedsubjects`, `optotagging`
- [ ] **MSW Monitor — Step 3: CLI + plotspec** — `msw monitor serve/status/debug` subcommands; `msw plotspec <task>` with `--dry-run`
- [ ] **MSW Monitor — Step 4: Docker** — `Dockerfile.monitor`, `docker-compose.monitor.yml`, Vue UI wired to monitor endpoints
- [ ] **MSW Monitor — Step 5: strip `agent/`** — after monitor validated on one rig
- [ ] `msw_flir_bonsai.timestamps` — finish user's existing unwrap code (FlyCapture 128s cycle), wire into `preprocess_camera_csv`; user has existing implementation to integrate
- [ ] **msw-openephys integration** (`msw-oe` CLI) — attach an Open Ephys session to a running MSW setup so session start confirms whether data will be written as an ephys child session or standalone. Goal: prevent ephys sessions left open and data ending up in the wrong directory. Operations: `msw-oe attach <setup>`, `msw-oe status`, `msw-oe detach`. Session start dialogue always checks OE status — even when not expected, to catch forgotten sessions. Integration point: MSW already has `is_child_session_to` plumbing (see `session_paths`); OE side uses the existing tool already made. Design sketch: `msw-oe` wraps the OE REST API; `TaskProcess` checks `msw-oe status` before `run_task()` and writes `child_session_dir` into session YAML.
- [ ] **`docs/tasks/` coverage** — add `calibration_and_test.md`; add task docs for `airpuff`, `optotagging` when those protocols are stable
- [ ] **post-acquisition pipeline in Python** — replace shell-script invocations in `msw post run` (`run_post_acquisition_tasks.sh`) with pure Python; provision_rpi scripts (`collate_data2.sh`, `upload_to_server.sh`, `h264_to_mp4.sh`) remain in `external/` (off-limits); Python wrapper would call them via subprocess or replicate logic; consider whether `inventory.ini` should live in `msw_configs/` (config dir) rather than alongside the scripts; see `docs/work_plans/PROVISION_RPI_SCRIPTS.md`

---

## DONE

- [x] msw-flir-bonsai camera integration — `FlirBonsaiClient`, `RceConductorAdapter`, `make_camera_client()` factory; `CameraConfig` FLIR fields; RCE module-level import bug fixed · 2026-05-22
- [x] MASTER_PLAN.md — single authoritative design doc, supersedes PLAN_msw_monitor + PLAN_msw_ui_agent_broadcast + AGENT_USAGE_MODEL + PLAN_hardware_manager · 2026-05-22
- [x] Sequence online plot — outcome dot offsets (±0.1 from perf line), no-response grey x at 0.5, perf-perfect yellow; `poke_xmax_s` param (default 6 s) · 2026-05-22
- [x] PlotSpec schema — `logic/plot_spec.py` pydantic validator; `sequence/plot_spec.yaml`, `probabilistic_switching_fixedsubjects/plot_spec.yaml`; 17 tests · 2026-05-22
- [x] `hardware/manager.py` — `DeviceProtocol` + `HardwareManager` context manager · 2026-05-22
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

**Setup-agent architecture (Stage-1 built, commit `98ed977`):**
One long-lived FastAPI process per rig. Bpod held open across sessions (inject `bpod=` into `TaskProcess`). Auth: HTTP Basic, `MSW_AGENT_PASSWORD` env var. Endpoints built: `/hardware/{status,reconnect}`, `/session/{active,start,events(WS)}`, `/config/{subjects,setups}`. Session start calls `evaluate_args()` — same config chain as CLI. WebSocket `/session/events` for trial event broadcast. Stage-2 adds: task→agent event wiring, `msw agent` CLI subcommand, heartbeat registration to central server. No DB, no mDNS, no web UI framework decided yet. See `docs/work_plans/PLAN_msw_ui_agent_broadcast.md`.

**ControllerSession (future):** extend `HardwareManager` to also hold Stage/PulsePal handles. `POST /hardware/action` dispatches hardware actions without stopping the session.
