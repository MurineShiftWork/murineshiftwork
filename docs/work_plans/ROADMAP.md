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
- [ ] **PyPI: publish RCC deprecation stub** — `rpi-camera-colony` stub pointing users to `rpi-camera-ensemble`; same pattern as `serial-weighing-scale` stub
- [ ] **GitHub: create repo + PyPI release for `rpi-camera-ensemble`** — push `external/provision_rpi/rpi_camera_ensemble`; ensure it is publicly installable (coexists with FLIR/Bonsai backend)
- [ ] **GitHub: create repo for `msw-flir-bonsai`** — push `external/msw-flir-bonsai`; publish to PyPI
- [ ] **git repo for `msw_configs/`** — move `/mnt/maindata/msw_configs` into a dedicated git repo to get clean history of setup/subject/calibration changes; MSW reads config_dir as before, just backed by git
- [ ] **Bonsai workflows — homogenise externalized properties** — add `cam1fps`, `cam1resolution` (width × height) to the Spinnaker workflows to match FlyCapture. Currently Spinnaker only externalises `cam1idx`; fps and resolution must be pre-set in SpinView. Approach: add `SpinnakerProperty` setter nodes for `AcquisitionFrameRate`, `Width`, `Height` before the `SpinnakerCapture` node, then add `ExternalizedMapping` entries for those nodes so `-p cam1fps=60` and `-p cam1width=1280 -p cam1height=1024` work at CLI launch. Verify on acquisition machine — camera must have `AcquisitionFrameRateEnable` set to `true` in SpinView first (one-time, persists in camera EEPROM). Once done, add `width`/`height` fields to `CameraUnit` model and pass them through `BonsaiCameraRunner._build_cmd()`.

---

## TODO

### Sprint order (2026-05-24)

1. ~~**Namespace — `file` level + `get_path(artifact=)`**~~ — **DONE** · 2026-05-24
2. **Opto debug** — review PR TODO items; hardware-verify optotagging TTL barcodes; confirm airpuff TTL barcodes; test on acquisition machine
3. **Namespace package separation** — extract `murineshiftwork` into namespace sub-packages per IMPLEMENTATION_PLAN.md extraction order
4. **msw-flir-bonsai** — `FlirBonsaiClient`, `make_camera_client()` factory, discriminated `CameraConfig` union in `models.py`; wire into `RceConductorAdapter`

---

- [ ] **Hardware handle + camera audit** — full sweep of all task protocols to verify: (1) correct use of injected hardware handles via `devices` dict (no fallback-to-new-connection in tasks that receive a handle); (2) camera handoff from config/hardware manager instead of ad-hoc constructor calls; (3) `serial_port_pulsepal`, `serial_port_scale` not opened twice. No action yet — audit only. Pending test protocols: `_test_scale_hx_connect` and `_test_scale_bench_connect` (same pattern as `_test_pulsepal_connect`).
- [ ] **Opto — hardware verification** — test optotagging and airpuff TTL barcodes on acquisition machine; alignment script for `sequence_automated` piecewise per-trial TTL edges not written
- [ ] **Opto — PR TODOs** — review opto PR notes for outstanding test items before closing branch
- [ ] **msw-flir-bonsai** — `FlirBonsaiClient`, `make_camera_client()` factory, discriminated `CameraConfig` union in `models.py`
- [ ] **msw-flir-bonsai — acquisition machine tests** — set `BONSAI_EXE`, run integration suite (`pytest tests/integration/ -v`); smoke-test CLI directly (`msw-flir find-bonsai`, `msw-flir list-cameras`, `msw-flir test-record`); run via `msw` task with `cameras.backend: flir_bonsai` in setup YAML to verify full `FlirBonsaiClient` path
- [ ] **Bpod retry — hardware verification** — test fixed retry on device `pci-0000:00:14.0-usb-0:4:1.0 → ttyACM7`; confirm 3-attempt / 2s-sleep resolves first-connect failures
- [ ] **MSW Monitor — Step 1: server + relay** — `monitor/relay.py` (`TrialRelay` daemon Process), `monitor/server.py` (FastAPI, in-memory SessionState, PlotSpec computation); see `MASTER_PLAN.md §5`
- [ ] **MSW Monitor — Step 2: TaskProcess wiring** — read `monitor_url` from machine config, start `TrialRelay`, add `put_nowait()` after `save_trial_data()` in `sequence`, `probabilistic_switching_fixedsubjects`, `optotagging`
- [ ] **MSW Monitor — Step 3: CLI + plotspec** — `msw monitor serve/status/debug` subcommands; `msw plotspec <task>` with `--dry-run`
- [ ] **MSW Monitor — Step 4: Docker** — `Dockerfile.monitor`, `docker-compose.monitor.yml`, Vue UI wired to monitor endpoints
- [ ] **MSW Monitor — Step 5: strip `agent/`** — after monitor validated on one rig
- [x] **Namespace builder wiring** — extend `namespace.msw.yaml` with `subject`+`acquisition` levels (optional); wire `generate_session_paths()` and `parse_session_basename()` through `NamespaceBuilder` methods; wire `OpenEphysParentSession.attach()` base_text parse through `extract_level_values` + `build_path` roundtrip. · 2026-05-25
- [ ] **`msw oe` + oe-remote extraction** — extract `external/msw_open_ephys/oe_remote/` to `MurineShiftWork/oe-remote`; add `msw oe status/preview/record/stop` delegating to `oe_remote.cli.commands`; replace `open_ephys.control` in `parent_session.py` with `oe_remote.controller` + namespace builder roundtrip for base_text validation. Full plan: `docs/work_plans/PLAN_oe_remote.md`.
- [ ] **Hardware integration test suite** — separate repo (not `tests/`); real Bpod + PulsePal + scale + OE GUI on acquisition machine; combinatorial runs of `sequence` + `optotagging` with/without `--parent openephys`; simulation-mode smoke tests; Bpod override API for automated trial progression; scope and repo structure TBD
- [ ] **Valve calibration fit model config** — `Calibrations.fit_model: exponential | linear` field in `models.py` (default `exponential`); written to setup YAML as `calibrations.fit_model:`; propagated to `ValveCalibration` instances on load; `ValveCalibration._fit()` branches on it; `evaluate.py` reads model from setup config when injecting `valve_s_for_ul`; calibration task reads same field as default, overridable via `-ts FIT_MODEL=linear` for one run. Design approved 2026-05-25.
- [x] **Valve calibration fallback + staleness warning** — `_inject_valve_calibration()` in `evaluate.py`: (1) port present → use, warn if >180 days stale; (2) `bpod_valve` empty → loud WARNING, use `_FALLBACK_VALVE_CALIBRATION` (npx2 reference, debug only); (3) some ports calibrated but requested port missing → hard `ValueError` with list of calibrated ports. `CALIBRATION_STALE_DAYS=180` in `models.py`. · 2026-05-25
- [ ] **`docs/tasks/` coverage** — add `calibration_and_test.md`; add task docs for `airpuff`, `optotagging` when those protocols are stable
- [ ] **post-acquisition pipeline in Python** — replace shell-script invocations in `msw post run` (`run_post_acquisition_tasks.sh`) with pure Python; provision_rpi scripts (`collate_data2.sh`, `upload_to_server.sh`, `h264_to_mp4.sh`) remain in `external/` (off-limits); Python wrapper would call them via subprocess or replicate logic; consider whether `inventory.ini` should live in `msw_configs/` (config dir) rather than alongside the scripts; see `docs/work_plans/PROVISION_RPI_SCRIPTS.md`

---

## DONE

- [x] OE parent session — `hardware/parent_session.py`: `ParentSessionProtocol`, `ParentSessionInfo`, `OpenEphysParentSession` (lazy OE import), `make_parent_session(type, **kw)` factory; `--parent TYPE[:URL]` CLI flag (URL falls back to `open_ephys_url` in machine config); `_resolve_parent_session()` + `_parse_parent_flag()` in evaluate.py; `parent_acquisition:` block in `.msw.session.yaml`; entrypoint plugin loader in parser.py (`msw.cli` group); 19 tests · 2026-05-25
- [x] `acquisition-namespace` standalone package — extracted from `murineshiftwork.namespace.spec`; `external/acquisition-namespace`; `NamespaceBuilder`, `NamespaceSpec`, `NamespaceLevelSpec`; fixed `_build_one` self-recursion bug; 25 tests; MSW `spec.py` now re-exports from it · 2026-05-24
- [x] namespace `file` level + `get_path(artifact=)` — `namespace.msw.yaml` `file` template; `get_msw_builder()` in `paths.py`; `msw_file()` delegates to builder (no hardcoded `.msw.` in Python); `TaskRunner.get_path()`; all raw `.msw.` replaced in `task_process.py`, `log.py`, task files; `readers/namespace.py` uses `is_msw_file()`; 23 tests · 2026-05-24
- [x] bench scale baudrate default 9600; `BenchScaleAdapter` + `ScaleDevice` + `make_scale` all corrected · 2026-05-24
- [x] HX711 retry — `SerialWeighingScaleAdapter.read_weight_blocking()` overrides hx711 internal retry; suppresses ERROR-level parse-failure spam, single WARNING summary · 2026-05-24
- [x] dynamic calibration — tqdm progress bar (`leave=False`) on drop loop; before/after weight delta (robust against bench-scale auto-zero) · 2026-05-24
- [x] pypulsepal LCD fix — space padding (not null bytes) + "PulsePal / Python fw{ver}" display text · 2026-05-24
- [x] execute.py device factory registry — `_DEVICE_REGISTRY` dict + lazy-import helpers replaces per-device if-chain in `run_task`; spurious pulsepal connection now prevented implicitly · 2026-05-24
- [x] pulsepal spurious connect fix — `evaluate.py` clears `serial_port_pulsepal` when setup config present but doesn't declare pulsepal; `execute.py` secondary guard · 2026-05-24
- [x] BUILD_SYSTEM_STANDARD.md rewrite + GH_CLI_REFERENCE.md — copier, Zenodo, vendoring, mypy v2 import-untyped gotcha · 2026-05-24
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
