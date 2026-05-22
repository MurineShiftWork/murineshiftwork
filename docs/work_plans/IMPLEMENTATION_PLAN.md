# MSW Implementation Plan

> **Architecture superseded by `MASTER_PLAN.md` (2026-05-22).** The gap table below remains
> the authoritative task-level status tracker; for all design decisions see `MASTER_PLAN.md`.
> Last updated 2026-05-20. Previous design ref: `PLAN_msw_ui_agent_broadcast.md` (archived).
> (deprecated with TODO comments only, not removed). Open questions in §5.

---

## 1. Architecture summary

```
agents.json  ──────────────────────────────────────────────────
  [{name, agent_url, cameras:[{name, stream_url}]}, ...]       │
                                                                │
external/msw-ui/  (Vue 3 + TS + Plotly.js)                    │
  Tab bar: setup-1 | setup-2 | npxb | ...                      │
  Per-tab: SessionHeader | CameraGrid | Metrics | PlotGrid      │
           OverridePanel (valve/LED/BNC buttons)                │
    ↕ HTTP poll every 2s / 5s                                   │
                                                                │
  Setup-agent  (FastAPI, port from SetupConfig.agent_port)     │
    /hardware/status|reconnect|action                           │
    /session/status|start|stop|plot-spec|plot                   │
    /config/subjects|tasks|task-modes/{task}|setup             │
    SessionManager: trial_buffer (deque), drain Thread          │
      ↑ queue.Queue.put_nowait() — fire-and-forget             │
    TaskProcess → TaskRunner(Thread)                            │
      TaskRunner.run() → Bpod state machine                    │
```

No central server or proxy. The CLI remains the primary interface; the web UI is a
per-machine monitoring layer that cannot block or affect task execution.

---

## 2. Gap analysis table

> Status as of 2026-05-20.

| Area | Status | Remaining gap |
|---|---|---|
| **Setup-agent core** | **DONE** — `agent/app.py`, `hardware_manager.py`, `session_manager.py`, `models.py`, `routers/` committed 98ed977. HTTP Basic auth via `MSW_AGENT_PASSWORD`. `msw agent start` works. | `POST /hardware/action` not wired to `BpodOverrideAPI`. `GET /config/tasks` and `/config/task-modes/{task}` not implemented. `msw agent stop/status` CLI subcommands missing. Trial event queue not injected into `TaskProcess`; `SessionManager` drain thread not started; `/session/status` returns static state only (no live counters). Agent tests not written. |
| **CLI: agent dispatch** | **NOT STARTED** | `_find_agent()` and `_dispatch_to_agent()` not in `execute.py`. `--no-agent` flag not on `msw run`. `msw run` still routes directly to `TaskProcess` only. |
| **Event queue bridge** | **NOT STARTED** | `TaskProcess.__init__` does not accept `event_queue` param. No tasks call `put_nowait()` after trial end. `SessionManager._drain_loop` and `_trial_buffer` not implemented. `/session/status` does not return `trial_count`, `reward_count`, `elapsed_s`. |
| **Incremental plot API** | **NOT STARTED** | No `plot:` block in any `task.yaml`. `agent/plot.py` not written. `/session/plot-spec` and `/session/plot?since_trial=N` endpoints not implemented. |
| **`msw-ui` Vue SPA** | **Scaffold done** — `external/msw-ui/` exists with Vite project, components, store, composables, Docker. | Not integrated against a running agent. `useAgentPolling.ts` and `stores/session.ts` still have drafted-but-unreviewed `GET /sessions` calls that must be removed (agent serves no history). Session history wiring (Option A: localStorage ring-buffer) not done. |
| **`POST /hardware/action`** | **NOT STARTED** | Route not in `agent/routers/hardware.py`. `BpodOverrideAPI` class is ready in `hardware/bpod/override.py`. |
| **Session history (Option A)** | **NOT STARTED** | `stores/session.ts` does not write history entry on `running→idle` transition. `SessionHeader` dropdown and `SessionHistory` table not wired to localStorage store. |
| **BpodOverrideAPI class** | **DONE** — `hardware/bpod/override.py`: `open_valve`, `close_valve`, `pulse_valve`, `close_all_valves`, `set_port_light`, `set_bnc`, `reward`. Uses `_write_lock`. | Nothing (class complete; needs wiring via `/hardware/action` endpoint). |
| **Optotagging unified config** | **DONE** — per-protocol `stimulation_defaults` + `stimulation` dict, `n_trials`/`iti`/`record_video`/`laser_power`, per-protocol video file, `deep_merge`. | Nothing. |
| **Sequence task** | **DONE** — dual scoring, no-response trials, regression fix, level-1 gate removed, online plot overhaul (a61dd65, a208732). | Nothing. |
| **Config overlay system** | **DONE** — `deep_merge`, config_dir overlay (steps 1–6), sticky `task_mode` writeback, sequence `start_level` writeback. | Nothing. |
| **Blockout timing log** | **Partial** — done in `sequence`, `probabilistic_switching`, `optotagging`. | Pending in: `airpuff`, `probabilistic_switching_fixedsubjects`, `sequence_automated`, `homecage_sleep`, `openfield`, `periodic_trigger`. Consider `log_trial_timing()` helper in `TaskRunner` to standardise format. |
| **Barcode/TTL** | **Done in code** — all tasks implemented; `logic/barcode.py` → `ttl_barcoder`; `readers/alignment.py` complete. | Hardware verification of optotagging and airpuff TTL barcodes still pending. Alignment script for `sequence_automated` (piecewise per-trial TTL edges) not written. |
| **Camera: CameraClient + FlirBonsaiClient** | **Partial** — `BonsaiCameraRunner`/`MultiCameraRunner` and `timestamps.py` in `external/msw-flir-bonsai/`. | `FlirBonsaiClient` not written. `make_camera_client()` factory not written. Discriminated `CameraConfig` union not in `models.py`. |
| **CLI** | **Mostly done** — `msw run`, `msw agent start`, `msw setup` (incl. rename), `msw subject`, `msw tasks`, `msw action`, `msw calibration`, `msw post`, `msw init`. | `msw agent stop/status` missing. `--no-agent` not on `msw run`. `msw ui` subcommand does not exist. |
| **Session files** | **Done** — `.msw.session.yaml` v2, JSONL, `barcode_value`/`barcode_wall_time`. | Session file schema doc (`session_file_schema.md`) not written. |
| **PyQt `online_plotting`** | **Stays** — PyQt plots continue running unchanged for now. | Add `# TODO(msw-ui): remove after msw-ui validated in production` comment to each `tasks/*/online_plotting.py`. No code removal until Stage 6 validated. |
| **OE integration** | **Partial** — `msw_open_ephys/` scaffolded. | Option A (`~/.cache/oe-remote/last_session` in `cli/evaluate.py`) not implemented. ~20-line change, no blockers. |
| **Calibration write-back** | **Not done** | `_calibration_liquid_*` tasks do not write back to setup YAML. `save_valve_calibration()` helper not written. No blockers. |
| **Reader library** | **In monolith** | Not yet extracted as `msw-readers` pip package. |

---

## 3. Implementation roadmap

> Stages follow `PLAN_msw_ui_agent_broadcast.md` §12 ordering.

### Agent sprint pre-work ✅ DONE

- [x] `BpodOverrideAPI` (`hardware/bpod/override.py`)
- [x] Blockout timing log: sequence, probabilistic_switching, optotagging
- [x] Vue UI scaffold (`external/msw-ui/`)
- [x] Agent core: `agent/` with hardware_manager, session_manager, routers, HTTP Basic auth

---

### Agent Stage 1 — Read-only endpoints ✅ DONE (98ed977)

`/hardware/status|reconnect`, `/session/status` (idle only), `/config/subjects|setups`,
`msw agent start` CLI subcommand. HTTP Basic auth wired.

**Remaining loose ends (do with Stage 2):**
- `GET /config/tasks` — scan task dirs, return `list[str]`
- `GET /config/task-modes/{task}` — load `task.yaml`, return mode keys
- `GET /config/setup` — serialise `SetupConfig`
- `msw agent stop` and `msw agent status` CLI subcommands
- `agent_port: int = 8765` field on `SetupConfig`

---

### Agent Stage 2 — Event queue bridge + live counters (next)

Goal: tasks emit per-trial dicts non-blocking; `/session/status` returns live `trial_count`,
`reward_count`, `elapsed_s`.

**`TaskProcess`** (`logic/task_process.py`):
- Add `event_queue: queue.Queue | None = None` to `__init__` (passed through `**kwargs` —
  no signature break for existing callers)
- Expose as `self._event_queue`

**Tasks** — one line after `save_trial_data()` in each main task loop:
```python
if self._event_queue is not None:
    try:
        self._event_queue.put_nowait({
            "trial_index": ..., "correct": ...,
            "reward_delivered": ..., "reward_volume_ul": ...,
            "timestamp": time.monotonic(),
        })
    except queue.Full:
        pass
```
Priority tasks: `sequence`, `probabilistic_switching_fixedsubjects`, `optotagging`.

**`SessionManager`** (`agent/session_manager.py`):
- Add `_event_queue: queue.Queue(maxsize=500)`
- Add `_trial_buffer: deque(maxlen=1000)`, `_counters`, `_lock: threading.Lock`
- Add `_drain_loop` daemon thread started at `__init__`
- Pass `event_queue` to `TaskProcess` at session start
- Update `/session/status` response to include live counters

**CLI dispatch** (do alongside Stage 2):
- `execute.py`: `_find_agent()` + `_dispatch_to_agent()` (polls `/session/status` until idle)
- `parser.py`: `--no-agent` flag on `msw run`; `stop`/`status` subcommands on `msw agent`

**Tests:** mock `HardwareManager` with `SimBpod`; test idle→running→idle; test drain loop
increments counters; integration test via FastAPI `TestClient`.

---

### Agent Stage 3 — Incremental plot API

Goal: Vue PlotGrid polls `/session/plot?since_trial=N` and appends to Plotly traces.

**`task.yaml` additions** (sequence first, others optional):
```yaml
plot:
  panels:
    - title: "Performance"
      type: rolling_mean
      field: correct
      window: 20
    - title: "Reward total"
      type: cumulative_sum
      field: reward_volume_ul
    - title: "Response latency"
      type: histogram
      field: response_latency_ms
      bins: 40
```

**New file:** `agent/plot.py` — `PlotSpec` loader + panel computation
(`rolling_mean`, `cumulative_sum`, `timeseries`, `histogram`, `scatter`). ~150 lines.
Reads from `trial_buffer` copy — no file I/O, no task thread contact.

**New endpoints** in `routers/session.py`:
- `GET /session/plot-spec` → parsed `PlotSpec` or `{panels: []}` when idle
- `GET /session/plot?since_trial=N` → `PlotUpdate` with `x_append`/`y_append` per panel

---

### Agent Stage 4 — Hardware override endpoint

Goal: `OverridePanel` in Vue UI sends valve/LED/BNC commands via HTTP.

**Modified:** `agent/routers/hardware.py` — add `POST /hardware/action`:
- Deserialise `ActionRequest`
- Instantiate `BpodOverrideAPI(hw.bpod)`
- Dispatch: `open_valve`, `close_valve`, `pulse_valve`, `set_port_light`, `set_bnc`, `reward`
- Return 409 if bpod not connected; uses existing `_write_lock`

---

### Agent Stage 5 — Session history (Option A)

Goal: UI shows recent sessions without any backend history endpoint.

- `stores/session.ts`: write localStorage entry (`msw_session_history_<name>`) on
  `running → idle` status transition; ring-buffer of 20 entries
- `SessionHeader` dropdown and `SessionHistory` table read from localStorage store
- Remove any `GET /sessions` or `GET /sessions/{id}` calls from `useAgentPolling.ts`
  and `stores/session.ts` (agent serves no history)

Option B (filesystem session-index service) deferred.

---

### Agent Stage 6 — PyQt deprecation markers

Add to each `tasks/*/online_plotting.py`:
```python
# TODO(msw-ui): remove after msw-ui online plotting validated in production.
#   Replaced by GET /session/plot (PlotSpec in task.yaml).
```
No code removed. PyQt plots continue running.

---

### Later — msw-ui integration + CLI wiring

- `msw ui` CLI subcommand: open browser to `external/msw-ui/index.html` (or serve via
  simple HTTP server from the Vue dist). Load `agents.json` from `config_dir`.
- When Vue UI is validated in production and all tasks have `plot:` blocks, remove PyQt
  `online_plotting.py` files one task at a time.

---

### Camera integration (after agent sprint stable)

- `FlirBonsaiClient` (`CameraClient` wrapper) in `external/msw-flir-bonsai/`
- `make_camera_client()` factory + discriminated `CameraConfig` union
- Wire camera lifecycle into `SessionManager`

---

### Namespace split + meta-package (last, blocked on all above stable)

Pure packaging work. Extract `msw-namespace`, `msw-logic`, `msw-agent`, `msw-readers` as
standalone pip packages with extras groups on the `murineshiftwork` meta-package.

---

## 4. Package split plan

Package prefix: **`msw-tasks-`** (plural — each package may contain more than one task file).

| pip name | Python namespace | Contents | Status |
|---|---|---|---|
| `murineshiftwork` (meta) | `murineshiftwork` | Meta-package; extras pull in task groups | **Monolith** — `__init__.py` removed at namespace root and tasks dir |
| `msw-namespace` | `murineshiftwork.namespace` | Path/filename generation | **In monolith** — extract last |
| `msw-logic` | `murineshiftwork.logic` + `.hardware` | Config, calibration, barcode, sounds, task_process | **In monolith** — extract last |
| `msw-agent` | `murineshiftwork.agent` | FastAPI setup-agent, routers, models | **In monolith — Stage 1 done** |
| `msw-tasks-core` | `murineshiftwork.tasks._calibration_*` + `._test_*` | Calibration tasks, test/flush tasks | **In monolith** — minimal deps; extract before lab tasks |
| `msw-tasks-sequence` | `murineshiftwork.tasks.sequence` | Sequence learning task + training levels | **In monolith** — must not import PyQt in agent path; extract after core |
| `msw-tasks-switching` | `murineshiftwork.tasks.probabilistic_switching` + `.probabilistic_switching_fixedsubjects` | Two-armed bandit (freely moving + head-fixed) | **In monolith** — depends on RCE; extract with camera client |
| `msw-tasks-other` | `murineshiftwork.tasks.{airpuff,optotagging,homecage_sleep,openfield,periodic_trigger*,exp_trn_spindle}` | Lab-specific protocols | **In monolith** — extract last; internal-use only |
| `msw-readers` | `murineshiftwork.readers` | Session data readers, alignment | **In monolith** — extract last |
| `msw-open-ephys` | `murineshiftwork.open_ephys` | OE attach/detach CLI | **Scaffolded in `external/`** — CLI integration incomplete |
| `msw-flir-bonsai` | `msw_flir_bonsai` | BonsaiCameraRunner, timestamps, alignment | **Partial** — runner + timestamps done; `FlirBonsaiClient` not written |
| `msw-ui` | n/a (Vue SPA) | Per-setup web monitoring UI | **Scaffold done** — `external/msw-ui/`; not yet integrated against agent |
| `one-axis-stage` | `one_axis_stage` | Stage tower driver | **Mature** |
| `ttl_barcoder` | `ttl_barcoder` | TTL barcode encoder/decoder | **Mature** |
| `pypulsepal` | `pypulsepal` | PulsePal laser driver | **In use** |

### Extraction order

1. `msw-tasks-core` (no heavy deps — good first-split test case)
2. `msw-tasks-sequence` (self-contained; agent path must stay PyQt-free)
3. `msw-logic` + `msw-namespace` (base layer; unblocks all others)
4. `msw-agent` (already structurally isolated)
5. `msw-readers` (no hardware deps)
6. `msw-tasks-switching` (depends on RCE/camera client being stable)
7. `msw-tasks-other` (last; internal-use, no urgency)

### Per-package documentation

Each extracted package gets its own `docs/` subtree shipped with the package:

| Package | Docs location |
|---|---|
| `msw-tasks-core` | `docs/tasks/calibration_and_test.md` (this repo until split) |
| `msw-tasks-sequence` | `docs/tasks/sequence.md` → moves to `msw-tasks-sequence/docs/` |
| `msw-tasks-switching` | `docs/tasks/probabilistic_switching*.md` → moves to `msw-tasks-switching/docs/` |
| `msw-logic` | Architecture and config system docs |
| `msw-agent` | Agent API reference |

Until a package is extracted, its docs live in `docs/tasks/` in the monolith.

---

## 5. Open design questions

1. **`step()` vs `run()` migration.** Tasks use `run()` loop; `BaseTask` ABC with `step()` not
   written. Decision: adopt `step()` now, or keep `run()` as v1 bridge? No blocker on agent sprint.

2. **`TaskProcess` Thread isolation.** Daemon Thread is fine for normal exceptions; a segfault or
   `os._exit()` from a C extension kills the whole agent. Keep Thread for v1; mitigate with
   `systemd Restart=on-failure`. Verify no blocking calls from async uvicorn routes (use
   `asyncio.to_thread` if needed).

3. **`agents.json` location.** Should live in `config_dir` (alongside `subjects/`, `setups/`).
   Needs a spec: format, `msw ui` discovery path, how `agent_port` in `SetupConfig` relates to it.

4. **`msw ui` delivery.** Does `msw ui` serve the Vue dist via a local HTTP server (simplest),
   or open `file://` directly (breaks `fetch()`)? Simplest: `python -m http.server` from
   `external/msw-ui/dist/`, open browser to `localhost:<random_port>`.

5. **Discriminated `CameraConfig` union.** Breaking change to existing setup YAMLs.
   Migration strategy needed before camera integration stage.

6. **OE child session (Option A).** Reading `~/.cache/oe-remote/last_session` in
   `cli/evaluate.py` is a ~20-line change. No blockers.

7. **Calibration write-back.** `_calibration_liquid_*` tasks do not write back to setup YAML.
   `save_valve_calibration()` helper not written. No blockers.

8. **`SimulatedAnimal`.** Mechanism verified (pybpodapi `socketin`). Implementing it would
   enable full end-to-end task tests without hardware — prerequisite for useful agent integration
   tests.

9. **Barcode hardware verification.** Optotagging and airpuff TTL barcodes coded but unverified
   on acquisition hardware. Alignment script for `sequence_automated` not written.

10. **Windows `msw run --no-agent`.** Win11 deployment uses direct `TaskProcess`. Must remain
    supported indefinitely under `--no-agent`.
