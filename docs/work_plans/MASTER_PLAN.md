# MSW Master Plan

*Created 2026-05-22. Branch `ft/msw-agent`.*

**This is the single authoritative design document.** It supersedes:
- `PLAN_msw_monitor.md`
- `PLAN_msw_ui_agent_broadcast.md`
- `AGENT_USAGE_MODEL.md`
- `PLAN_hardware_manager.md`

`IMPLEMENTATION_PLAN.md` gap table remains valid for task-level status; this document governs architecture.

---

## 1. Architecture principles (locked — no exceptions)

| Principle | Consequence |
|---|---|
| **CLI starts all sessions.** `msw run` is the only session entry point. | Agent/monitor can never call `evaluate_args()` or `TaskProcess()`. |
| **Data durability is in-process.** JSONL + session YAML written inside the task process. | Session is fully recorded even if monitor is down. |
| **Network never blocks the task loop.** All outbound sends are fire-and-forget, non-blocking. | `put_nowait()` in the task loop, HTTP POST in a daemon process. |
| **Monitor is best-effort read-only.** No control actions via the monitor in v1. | Session start/stop/stop only via CLI or HardwareManager context. |
| **Hardware is injected, not owned by tasks.** Tasks receive ready-to-use handles. | No `BpodFactory` import inside task code. |
| **Bpod is not special.** It is one implementation of `DeviceProtocol`. | Future Harp/PyControl devices slot in without changing task code. |

---

## 2. Package structure

```
murineshiftwork/                      main package
  cli/
    parser.py                         argparse definitions
    evaluate.py                       session orchestration (per-task evaluate fns)
    preflight.py                      pre-run config validation
    execute.py                        session execution (to be updated: HardwareManager wiring)
  hardware/
    manager.py                        DeviceProtocol + HardwareManager (done)
    bpod/
      factory.py                      BpodFactory — retry logic (done)
      device.py                       BpodDevice(DeviceProtocol) — PLANNED
    camera/
      client.py                       make_camera_client() + adapters (done)
  logic/
    task_process.py                   TaskProcess — session thread lifecycle
    plot_spec.py                      PlotSpec pydantic model + loader (done)
    config/
      models.py                       SetupConfig, CameraConfig, DeviceUnion (done)
  monitor/
    relay.py                          TrialRelay daemon process — PLANNED
    server.py                         FastAPI monitor server — PLANNED
  tasks/
    sequence/
      plot_spec.yaml                  PlotSpec for sequence task (done)
      online_plotting.py              pyqtgraph live plot process (done)
    probabilistic_switching_fixedsubjects/
      plot_spec.yaml                  PlotSpec (done)
  agent/                              DEPRECATED — strip after monitor validated

external/ (off-limits — read/reference only)
  msw-flir-bonsai/                    FLIR camera via Bonsai subprocesses
  msw-ui/                             Vue 3 + Plotly.js SPA
  serial_scale_hx711/
  serial_scale_bench/
```

---

## 3. Hardware manager

### DeviceProtocol interface

```python
class DeviceProtocol(Protocol):
    name: str                    # key in devices dict, e.g. "bpod"
    def preflight(self) -> None  # check port reachable; raise IOError/ValueError
    def connect(self) -> None    # open connection; raise RuntimeError after retries
    def disconnect(self) -> None # close gracefully; never raises
    @property
    def handle(self) -> Any      # raw object passed to task (e.g. BpodFactory instance)
```

File: `hardware/manager.py` — `DeviceProtocol`, `HardwareManager` — **done**.

### HardwareManager usage

```python
with HardwareManager([BpodDevice(port)]) as devices:
    TaskProcess(bpod=devices["bpod"], ...)
```

`__enter__` calls `preflight()` then `connect()` on each device; `__exit__` calls `disconnect()` in reverse order regardless of exceptions.

### BpodDevice (planned)

File: `hardware/bpod/device.py`

```python
class BpodDevice:
    name = "bpod"
    def __init__(self, serial_port, connect_retries=3, retry_delay_s=2.0): ...
    def preflight(self):   test_serial_port_is_accessible(port)
    def connect(self):     BpodFactory(port, ...).open()   # retry loop inside
    def disconnect(self):  factory.close_safely()
    @property handle:      factory  # BpodFactory proxied as Bpod
```

### Session call chain

```
msw run
  → execute.py: build_device_list(setup_config)
  → HardwareManager([BpodDevice(port)])
  → HardwareManager.__enter__()
    → BpodDevice.preflight()  →  test_serial_port_is_accessible(port)
    → BpodDevice.connect()    →  BpodFactory(port).open()
      → BpodFactory.open()    →  _create_bpod_object()  [retry loop, up to 3×]
        → Bpod(port)          →  BpodCOMProtocol.open()  →  serial.Serial(port)
  → returns {"bpod": BpodFactory}
  → TaskProcess(bpod=devices["bpod"], ...)
  → TaskProcess.init_task()  →  Task(bpod=devices["bpod"], **kwargs)
  → TaskRunner.run()
    → StateMachine(bpod=self.bpod)
    → bpod.send_state_machine(sma)
    → bpod.run_state_machine(sma)
  → session end
  → HardwareManager.__exit__()
    → BpodDevice.disconnect()  →  BpodFactory.close_safely()
```

### Replaceable hardware note

> `SetupConfig.devices` expresses device type as a string key (e.g. `type: bpod`).
> When Harp or PyControl support is added, those backends implement `DeviceProtocol`
> identically and are selected by the `type` field — no task code changes.
> Some tasks already run without Bpod (`require_bpod=False`); this is the first-class path.
> **Review item**: ensure no task imports `BpodFactory` directly; all hardware access
> via the injected handle from `HardwareManager`.

---

## 4. Camera integration

Full design: `docs/work_plans/PLAN_camera_integration.md`.

### Principle

MSW owns the interface, not the implementation. Camera-specific logic
(workflow loading, subprocess dispatch, agent discovery, camera enumeration)
belongs in the plugin package (`rpi_camera_ensemble`, `msw_flir_bonsai`).

### Minimal CameraClient interface (Protocol)

```
conductor.preflight()                        # check paths / connectivity
conductor.start_recording(path, name)        # begin writing frames
conductor.stop_recording()                   # flush + finalise
conductor.teardown()                         # disconnect / terminate
```

Task code calls only these four methods. The 7-method API (`setup_agents`,
`initialize_acquisition`, `start_preview`, etc.) is **retired** — those were
RCE-specific steps that leaked into a shared interface.

### Call chain

```
evaluate function
  → make_camera_client(cameras_config=SetupConfig.cameras)
  → conductor.preflight()          # raises ValueError/ConnectionError on failure
  → [TaskProcess built — session path + name available]
  → conductor.start_recording(out_path, session_name)
  → [task runs]
  → conductor.stop_recording()
  → conductor.teardown()
```

### Adapters

**RceConductorAdapter** (`backend="rce"`): `start_recording()` runs the full
RCE sequence internally (setup agents → initialize acquisition → start
recording). MSW does not see the steps.

**FlirBonsaiClient** (`backend="flir_bonsai"`): `preflight()` checks
`bonsai_exe` path. `start_recording()` defers `msw_flir_bonsai` import,
constructs `MultiCameraRunner`, and calls `runner.start()`.

### Bonsai path (Windows)

Bonsai installs to `%LOCALAPPDATA%\Bonsai\Bonsai.exe` — not in PATH. `where
bonsai` typically fails. Use the `bonsai_exe` field in `CameraConfig`, or the
`BONSAI_EXE` environment variable. `msw flir find-bonsai` can scan known
paths (see plugin CLI below).

### Plugin CLI — `msw flir` subcommands

`msw-flir-bonsai` registers hardware-inspection subcommands via Python
entry points. MSW discovers them at startup:

```python
for ep in importlib.metadata.entry_points(group="msw.cli"):
    app.add_typer(ep.load(), name=ep.name)
```

If `msw-flir-bonsai` is not installed, `msw flir` simply does not exist.

Proposed subcommands: `msw flir list-cameras`, `msw flir check-config <path>`,
`msw flir find-bonsai`, `msw flir test-record`.

The entry-point loader is one small loop added to MSW CLI initialisation —
no other MSW code changes required.

### SetupConfig cameras YAML

```yaml
cameras:
  backend: rce
  config: /mnt/maindata/msw_configs/cameras/npxb_ensemble.yaml

cameras:
  backend: flir_bonsai
  n_cameras: 2
  fps: 60
  driver: spinnaker
  bonsai_exe: C:\Users\lab\AppData\Local\Bonsai\Bonsai.exe
```

---

## 5. Monitor pipeline

### Architecture

```
msw run (CLI process)
  └── TaskProcess.__init__
        ├── TrialRelay.start()          daemon Process, reads from mp.Queue
        └── TaskRunner (Thread)
              └── task loop: after save_trial_data()
                    queue.put_nowait(raw_trial_dict)    ← ~1 µs, never blocks

TrialRelay (multiprocessing.Process, daemon=True)
  └── queue.get(block=True, timeout=5)
  └── HTTP POST /ingest/{setup}/trial  →  monitor server
        ├── failure: logging.debug(), drop silently (0 retries)
        └── HTTP timeout: 0.5 s

msw monitor serve  (FastAPI, port 8080, in Docker)
  ├── POST /ingest/{setup}/start   ← session start: task, subject, plot_spec
  ├── POST /ingest/{setup}/trial   ← per-trial raw dict
  ├── POST /ingest/{setup}/stop    ← session end summary
  ├── GET  /session/status/{setup} ← {state, trial_count, reward_count, elapsed_s}
  ├── GET  /session/plot/{setup}?since_trial=N  ← panel updates
  ├── WS   /events/{setup}         ← push on trial complete
  └── GET  /session/history/{setup} ← ring buffer, last 20 sessions

Vue UI (served from same container)
  └── polls /session/status every 2 s
  └── polls /session/plot every 5 s (when running)
  └── subscribes to WS /events for trial notification
```

### Non-blocking guarantee

```
Task loop (hot path)             TrialRelay (daemon process)
─────────────────────────        ──────────────────────────
save_trial_data()                while True:
try:                                 event = queue.get(block=True, timeout=5)
    q.put_nowait(raw_dict)           try:
except queue.Full:                       _http_post(event, timeout=0.5)
    pass   ← ~0 µs drop             except Exception:
                                         logging.debug(...)
```

- `Queue(maxsize=500)` — ~500 trial buffer if monitor is slow or down
- `put_nowait`: single lock+check, ~1 µs regardless of network state
- `TrialRelay` crash → daemon=True, no zombie; task continues
- Monitor down → HTTP times out in 0.5 s, caught silently in TrialRelay

### TrialRelay implementation sketch

File: `murineshiftwork/monitor/relay.py`

```python
class TrialRelay(multiprocessing.Process):
    def __init__(self, queue, monitor_url, setup): ...
    def run(self):
        while True:
            try:
                event = self._queue.get(block=True, timeout=5)
                if event is None: break     # sentinel → clean shutdown
                self._post("trial", event)
            except Exception:
                pass

    def _post(self, endpoint, payload):
        url = f"{self._monitor_url}/ingest/{self._setup}/{endpoint}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=0.5)
        except Exception as exc:
            logging.debug("TrialRelay POST failed (%s): %s", endpoint, exc)
```

### TaskProcess wiring sketch

In `TaskProcess.__init__` (after `session_paths` is set):
```python
monitor_url = read_machine_config().get("monitor_url", "")
if monitor_url:
    self._relay_queue = multiprocessing.Queue(maxsize=500)
    self._relay_proc = TrialRelay(self._relay_queue, monitor_url, setup=self.setup)
    self._relay_proc.start()
    # POST session start event (subject, task, plot_spec)
```

Tasks use:
```python
# at end of each trial:
if relay_queue is not None:
    try:
        relay_queue.put_nowait({
            "trial_index": trial_index,
            "outcome": outcome,
            "reward_delivered": reward_delivered,
            "reward_volume_ul": reward_volume_ul,
            "timestamp": time.monotonic(),
        })
    except queue.Full:
        pass
```

### monitor_url config

```yaml
# ~/.murineshiftwork/msw_machine.yaml
monitor_url: http://localhost:8080   # absent = no relay started
```

---

## 6. PlotSpec

### Schema

File: `logic/plot_spec.py` — pydantic validator — **done**.
YAML files: `tasks/*/plot_spec.yaml` — done for `sequence`, `probabilistic_switching_fixedsubjects`.

```yaml
version: 1
task: sequence
panels:
  - id: outcomes_perf
    title: "Outcomes & rolling performance"
    type: rolling_mean           # rolling_mean | timeseries | cumulative_sum | histogram | raster | scatter
    fields:
      x: trial_index
      value: perf_buffer_mean
      scatter_flag: is_correct
    options:
      y_correct: 1.1
      y_incorrect: -0.1
```

### Panel types and required fields

| Type | Required fields | Description |
|---|---|---|
| `rolling_mean` | `x`, `value` | Rolling average line + optional scatter |
| `timeseries` | `x`, `value` | Line plot vs trial or time |
| `cumulative_sum` | `x`, `value` | Cumulative sum vs time |
| `histogram` | `value` | Distribution histogram |
| `raster` | `x`, `times` | Event raster (poke times per trial) |
| `scatter` | `x`, `y` | Scatter plot with optional color field |

### Single source of truth pattern

`online_plotting.py` files read field names from the spec to avoid hardcoding trial dict keys:

```python
_SPEC = PlotSpec.from_yaml(Path(__file__).parent / "plot_spec.yaml")
# In update callback:
d[_SPEC.panel("outcomes_perf").fields["value"]]  # → "perf_buffer_mean"
```

---

## 7. Full session call chain

```
user: msw run --setup npxb --subject AA001 --task sequence

parser.py: parse_args()  →  args_dict
evaluate.py: evaluate_args(args_dict)
  → _evaluate_and_load_configs()
    → SetupConfig.from_yaml(setup.yaml)
      → args_dict["cameras_config"] = setup_config.cameras
      → args_dict["config_file_camera"] = cameras.config  (RCE compat)
  → build_task_settings()  →  patched settings (5-level priority chain)
  → preflight(args_dict)   →  serial port accessible? camera config present?

[task-specific evaluate function, e.g. sequence.evaluate()]
  → make_camera_client(cameras_config, ...)  →  conductor (or None)
  → data_queue = multiprocessing.Queue()
  → kill_queue = multiprocessing.Queue()

  → with TaskProcess(bpod=None, ...) as tp:
      → HardwareManager([BpodDevice(port)]).__enter__()  [PLANNED]
          → BpodDevice.preflight()  →  test_serial_port_is_accessible()
          → BpodDevice.connect()    →  BpodFactory(port).open()  [3 retries, 2s sleep]
      → TaskProcess.__init__
          → session_paths = build_data_paths(...)
          → mkdir(session_folder)
          → add_session_log_handler(session_file_path)
          → persist_settings()  →  write .msw.session.yaml
          → monitor_url = read_machine_config().get("monitor_url")  [PLANNED]
          → TrialRelay.start()  [PLANNED, if monitor_url set]
          → collect_hooks(setup_config, task_settings)
          → run_pre_hooks(...)
          → init_task()  →  Task(bpod=devices["bpod"], **input_kwargs)
          → run_task()   →  task_thread.start()

      → conductor.initialize_acquisition(path, name)
      → conductor.start_recording()

      → OnlinePlottingForSeq.start()  [separate Process]

      → while tp.is_running():
            time.sleep(1)  [KeyboardInterrupt → tp.stop_task()]

      → task_thread finishes
      → save_session_end()  →  update .msw.session.yaml
      → relay_queue.put_nowait(None)  [sentinel → TrialRelay shutdown]

  → TaskProcess.__exit__()
      → run_post_hooks(...)
      → exit_safely()  →  bpod.close_safely()  [or HardwareManager.__exit__()]

  → conductor.stop_acquisition(); conductor.stop()
  → OnlinePlottingForSeq: kill_queue.put(True)
```

---

## 8. Task config key naming conventions

Configs stay **flat** (no nesting). These rules apply to all tasks.

### Cross-task shared names

When a param appears in multiple tasks it must use the same key name:

| Concept | Canonical key |
|---|---|
| Soft-stop trial limit | `stop_trials` |
| Soft-stop total reward | `stop_reward_ul` |
| Soft-stop time | `stop_time_min` |
| Max trials before forced end | `n_max_trials` |
| ITI duration (single float) | `iti_duration_s` |
| Online plot trial window | `online_plot_xlim_trials` |
| Live plot toggle | `show_live_plot` |

### Prefix groups

| Prefix | Covers |
|---|---|
| `online_plot_` | All live-plot display params |
| `stop_` | Soft-stop criteria (time / trial / reward / level limits) |
| `HARDWARE_` | All Bpod I/O mappings: ports, BNCs, lick events |
| `barcode_` | TTL barcode params (shared across tasks) |
| `reward_sound_` | Reward tone params |
| `stop_signal_` | Stop-signal paradigm trial params (fixedsubjects) |
| `stimulation_` | Optogenetic / electrical stimulation params |

Note: `stop_signal_*` and `stop_*` are **distinct** prefixes serving different
concepts. Do not use `stop_trial_*` for stop-signal paradigm — that prefix
collides with soft-stop criteria.

### Duration / unit suffixes

- Durations in seconds: `_s` or `_duration_s` suffix. Exception: `iti_duration_s`
  is the canonical name even though it is redundant.
- Durations in milliseconds: `_ms` suffix.
- Volumes: `_ul` suffix.
- Do **not** mix unitless duration keys (`iti_duration`, `punish_duration`) with
  suffixed keys in the same task.

### Boolean flags

Use `*_enabled` suffix. Avoid `use_*` prefix and `*_bool` suffix.

### Hardware constants

`HARDWARE_*` keys are uppercase throughout. Lick event names follow the same
convention: `HARDWARE_LICK_LEFT`, `HARDWARE_LICK_RIGHT` (not `LICK_EVENT_*`).

### Known naming debt (to fix before next fixedsubjects release)

| Current key | Should be |
|---|---|
| `stop_trial_*` (10 keys) | `stop_signal_*` |
| `punish_stop_trials` | `stop_signal_punish_enabled` |
| `punish_stop_trials_proportion` | `stop_signal_punish_proportion` |
| `LICK_EVENT_LEFT/RIGHT` | `HARDWARE_LICK_LEFT/RIGHT` |
| `use_stop_trials` | `stop_signal_enabled` |
| `use_stimulation` | `stimulation_enabled` |
| `use_piezo_lick_detection` | `piezo_lick_detection_enabled` |
| `inter_trial_interval` | `iti_distribution` (it is a [min, max, step] list) |
| `plot_trial_span` | `online_plot_xlim_trials` |
| `delay_until_center_init` | `center_init_timeout_s` |
| `delay_until_side_timeout` | `side_choice_timeout_s` |
| `stage_anti_bias_bool` | `anti_bias_enabled` |
| `state_duration_final` | `final_state_duration_s` |

---

## 9. Remaining work (ordered)


### Done: ft/msw-agent → merged to main 2026-05-22

- [x] Bpod retry fix — `BpodFactory.__init__` no longer auto-connects; retry loop in `open()`
- [x] `probe_bpods.py` script — connect all setups sequentially, print hardware info box
- [x] Sequence online plot — outcome dot offsets (±0.1), no-response grey x, perf-perfect yellow; stop label fix (800 µL not "1 ml"); poke x-axis `poke_xmax_s` param default 6 s
- [x] PlotSpec schema — `logic/plot_spec.py`, `tasks/sequence/plot_spec.yaml`, `tasks/probabilistic_switching_fixedsubjects/plot_spec.yaml`, 17 tests
- [x] `hardware/manager.py` — `DeviceProtocol` + `HardwareManager` context manager
- [x] Camera integration — `CameraConfig`, `FlirBonsaiClient`, `RceConductorAdapter`, `make_camera_client()` factory; minimal 4-method interface; plugin CLI design documented
- [x] Config upgrade design — on-load warning only; `msw config upgrade` CLI documented in `config_system.md`
- [x] Task config key naming conventions — prefix rules, naming debt table for fixedsubjects, in `MASTER_PLAN §8`
- [x] Fix calibration import — `bpod.water` → `bpod.valve` in both `_calibration_liquid_*` tasks

---

### Done: ft/hardware-wiring → merged to main 2026-05-22

- [x] `hardware/bpod/device.py` — `BpodDevice(DeviceProtocol)`
- [x] `HardwareManager` wired into `execute.py`; `TaskProcess` accepts `devices` dict
- [x] `BpodFactory.__getattr__` fixed — `_hardware` and other `_`-prefixed attrs proxy after connect
- [x] 28 hardware manager tests; 2 `BpodFactory.__getattr__` regression tests
- [x] `docs.yml` CI workflow deleted (Python 3.10 incompatibility, unwanted public Pages deploy)

---

### Branch: ft/monitor-step1 (PR-ready)

Architecture redesign — see `docs/work_plans/PLAN_logagent_ui.md`.
Key changes: `monitor/` → `logagent/`; `TrialRelay` → `LogAgent`; session UUID;
hardware-blind `trial_data`; bearer token auth; `log_url` + `log_bearer_token` in machine config.

- [x] `logagent/logagent.py` — `LogAgent` daemon: three-phase lifecycle (start/trial/stop POSTs), session_uuid tagged on all payloads, bearer token header
- [x] `logagent/server.py` — FastAPI ingest + status; bearer token validation on ingest; session_uuid stored
- [x] `TaskProcess._start_relay()` — reads `log_url` + `log_bearer_token` from machine config; optional (no-op if `log_url` absent)
- [x] `TaskProcess.__init__` — generates `session_uuid` (uuid4); persists in session YAML
- [x] `TaskProcess.init_task()` — copies `plot_spec.yaml` → `{session}.msw.plot_spec.yaml` if task has one
- [x] `put_nowait()` in sequence task after each trial
- [x] Step-wise INFO logging: HardwareManager preflight/connect/ready, hook names, session identity
- [x] `--port-*` flags marked DEPRECATED in CLI help
- [x] `msw monitor` CLI subcommand removed (server started externally)
- [x] `fastapi`, `httpx`, `uvicorn` added to dev extras
- [x] Tutorial docs plan — `PLAN_tutorial_docs.md`
- [x] LogAgent + UI architecture plan — `PLAN_logagent_ui.md`
- [x] Tests: 30 passing

Next after merge: ft/monitor-step2 — `trials?since=N` endpoint + `msw plotspec` CLI (see `PLAN_logagent_ui.md`)

---

### Branch: ft/device-flag

- [ ] **`--device name:path`** — single repeatable flag replacing all `--port-*` flags
  - Parses `bpod:/dev/ttyACM7` → `{"bpod": "/dev/ttyACM7"}`; merges with setup config device ports
  - `--port-*` flags removed once `--device` is in and callers updated
  - Remove `serial_port_bpod` / `require_bpod` from `TaskProcess` (pass hardware via `devices=` only)
  - See FLIR plugin CLI entry-point loader in `cli/parser.py` (same branch or companion)

---

### Branch: ft/monitor-step2 (after step 1 validated on rig)

- [ ] **`msw plotspec <task>`** — load + print PlotSpec YAML; `--dry-run` generates synthetic data and prints panel updates
- [ ] **Verify `LogAgent` fields** — sequence and fixedsubjects first; extend to optotagging

---

### Branch: ft/monitor-step3 (Docker + Vue)

- [ ] **`Dockerfile.monitor`** + `docker-compose.monitor.yml` — two containers: nginx (Vue dist) + FastAPI (API)
- [ ] **Vue UI wiring** — polling `/sessions` + `/sessions/{uuid}/trials?since=N`; PlotSpec-driven Plotly panels

---

### Branch: ft/monitor-step4 (strip agent/)

- [ ] Strip `agent/` package after LogAgent + UI validated on one rig
- [ ] Remove `msw agent start` CLI subcommand

---

### Branch: ft/tutorial-docs

- [ ] Write tutorial pages 00, 02, 05, 07, 08 (priority gaps) — see `PLAN_tutorial_docs.md`
- [ ] Rewrite `getting_started/` into tutorial series structure

---

### Branch: ft/config-upgrade

- [ ] **`msw config upgrade task/setup/subject`** — dry-run diff, confirmation prompt, `.bak` before write, `msw_schema_version` bump; `--yes` for scripted use
- [ ] **On-load version warning** — detect `msw_schema_version` mismatch, print one-time console warning, never auto-write

---

### Branch: ft/fixedsubjects-naming

- [ ] **Rename `stop_trial_*` → `stop_signal_*`** (10 keys) — update task.yaml, task_objects.py, all overlay YAMLs, docs
- [ ] **`LICK_EVENT_*` → `HARDWARE_LICK_*`**, `use_*` → `*_enabled`, `inter_trial_interval` → `iti_distribution`, `plot_trial_span` → `online_plot_xlim_trials`, timeout/delay key renames per §8 debt table
- [ ] **Update subject YAMLs in `msw_configs/`** — run migration script or manual update before merge

---

### Other open items (no branch yet)

- [ ] **Blockout timing log** — `airpuff`, `sequence_automated`, `homecage_sleep`, `openfield`, `periodic_trigger`
- [ ] **`msw-openephys`** — `msw-oe attach/status/detach`; session start checks OE status
- [ ] **Calibration write-back** — `_calibration_liquid_*` tasks write results back to setup YAML
- [ ] **Session file schema doc** — complete skeleton at `docs/concepts/session_files.md`
- [ ] **`msw_flir_bonsai.timestamps`** — finish FlyCapture 128 s cycle unwrap; wire into `preprocess_camera_csv`
- [ ] **`msw flir` plugin CLI** — implement entry-point loader loop in MSW CLI; add subcommands in `msw-flir-bonsai`

---

## 10. Superseded documents

| Document | Status | Superseded by |
|---|---|---|
| `PLAN_msw_monitor.md` | Superseded | This document §5 |
| `PLAN_msw_ui_agent_broadcast.md` | Superseded | This document §2, §5 |
| `AGENT_USAGE_MODEL.md` | Superseded | This document §1 |
| `PLAN_hardware_manager.md` | Superseded | This document §3 |
| `IMPLEMENTATION_PLAN.md` | **Active** — gap table still valid | Architecture superseded by this doc |

---

## 11. Key file locations

| Concern | File |
|---|---|
| Machine-local config | `~/.murineshiftwork/msw_machine.yaml` |
| Setup configs | `/mnt/maindata/msw_configs/setups/setup-*.yaml` |
| Session crash-recovery backup | `~/.murineshiftwork/sequence/` |
| Central session logs | `~/.murineshiftwork/logs/<setup>--<dt>--<subject>--<task>.log` |
| Hardware manager | `hardware/manager.py` |
| Camera factory | `hardware/camera/client.py` |
| PlotSpec model | `logic/plot_spec.py` |
| PlotSpec files | `tasks/*/plot_spec.yaml` |
| Monitor server (planned) | `monitor/server.py` |
| Monitor relay (planned) | `monitor/relay.py` |
