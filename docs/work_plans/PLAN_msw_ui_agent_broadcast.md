# MSW UI + Agent Broadcast Design Plan

> Status: design 2026-05-19. Supersedes relevant sections of DRAFT_agent_architecture.md.
> Decisions locked: Vue 3 + TS + Plotly.js, Option C (static agents.json, no central server for intermediate product).

---

## 1. Constraints

**Non-negotiable: API must never block or fail the task thread.**

The CLI-driven `TaskRunner` is a `threading.Thread`. The setup-agent's FastAPI server runs in a **daemon thread** in the same process. Both share the GIL. The constraint is enforced by:

1. The task thread only writes to the event queue (`queue.Queue.put_nowait`). Non-blocking, fire-and-forget. `queue.Full` → drop silently.
2. All API reads come from `SessionManager`'s own buffer, never from `TaskProcess` or `TaskRunner` directly.
3. The buffer lock is held only for the duration of a list copy (`< 1 µs`). Computation on the copy happens unlocked.
4. GIL contention is negligible in practice: `run_state_machine()` blocks on serial I/O, which releases the GIL. API compute runs during that window. The blockout compute window (~10–50 ms) has a low probability of coinciding with an API poll (every 5 s). Numpy operations also release the GIL.

---

## 2. Data broadcast: task → agent → UI

### 2.1 Event queue (task → SessionManager)

One `queue.Queue(maxsize=500)` created by `SessionManager` at session start. Passed to `TaskProcess` at construction:

```python
class TaskProcess:
    def __init__(self, ..., event_queue=None):
        self._event_queue = event_queue
```

Tasks emit after each trial end (non-blocking):

```python
if self._event_queue is not None:
    try:
        self._event_queue.put_nowait({
            "trial_index": self.trial_count,
            "correct": bool(outcome.correct),
            "reward_delivered": bool(outcome.reward_delivered),
            "reward_volume_ul": float(outcome.reward_volume_ul),
            "timestamp": time.monotonic(),
        })
    except queue.Full:
        pass  # UI is behind; drop
```

The task code never blocks, never imports from agent, never knows the queue exists if not injected. Identical isolation principle to RCE `AcquisitionProcess` → `response_queue`.

### 2.2 SessionManager buffer (agent-internal)

`SessionManager` owns the queue and drains it in a background daemon thread:

```python
class SessionManager:
    def __init__(self):
        self._event_queue: queue.Queue = queue.Queue(maxsize=500)
        self._trial_buffer: collections.deque = collections.deque(maxlen=1000)
        self._counters = {"trial_count": 0, "reward_count": 0, "reward_total_ul": 0.0}
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._drain_loop, daemon=True)

    def _drain_loop(self):
        while True:
            try:
                event = self._event_queue.get(timeout=1.0)
                with self._lock:
                    self._trial_buffer.append(event)
                    self._counters["trial_count"] += 1
                    if event.get("reward_delivered"):
                        self._counters["reward_count"] += 1
                        self._counters["reward_total_ul"] += event.get("reward_volume_ul", 0)
            except queue.Empty:
                continue
```

API handlers read from `_trial_buffer` and `_counters` only. Lock held for copy only:

```python
def get_trials_since(self, since_index: int) -> list[dict]:
    with self._lock:
        buf = list(self._trial_buffer)
    return [t for t in buf if t["trial_index"] > since_index]
```

### 2.3 Transport: polling (intermediate product)

No WebSocket for v1. Browser polls two endpoints:

| Endpoint | Poll interval | Notes |
|---|---|---|
| `GET /session/status` | 2 s | state, subject, task, trial_count, reward_count, elapsed_time |
| `GET /session/plot?since_trial=N` | 5 s when running | incremental Plotly trace updates from trial N |
| `GET /session/plot-spec` | once per session | task's plot: YAML block → Plotly layout skeleton |

Both endpoints return within 20 ms. If agent unreachable → Vue retries next poll → shows stale badge (same pattern as camera stream page). No connection state to manage.

SSE (one-way server push of trial events) can be added in Stage 6 for live trial counter updates. WebSocket deferred to Stage 6 interactive mode.

---

## 3. Incremental plot updates and UI state persistence

**Problem:** at 5 Hz trial rate, 100 trials/session, sending all trial data on every 5 s poll means sending an ever-growing payload. By trial 500 it's 500 records per response.

**Solution: cursor-based incremental endpoint.**

`GET /session/plot?since_trial=N` → agent returns only Plotly trace UPDATES (new data points for trials > N), not full raw records:

```json
{
  "since_trial": 142,
  "last_trial": 158,
  "panels": [
    {
      "title": "Performance",
      "x_append": [143, 144, 145, ...],
      "y_append": [0.72, 0.74, 0.71, ...]
    }
  ]
}
```

Vue client appends `x_append` / `y_append` to existing Plotly traces via `Plotly.extendTraces()`. Response size is always O(new_trials_since_last_poll), not O(total_trials).

**Page refresh persistence:** Pinia store serialises accumulated trace arrays to `localStorage` on every update. On mount, store rehydrates from localStorage and resumes polling from `last_trial`. Stored data ~1–2 KB per 1000 trials.

Store key: `msw_session_<setup_name>`. Clear on `session_end` event or when new session detected (session_id mismatch).

---

## 4. PlotSpec: task-owned plot definition

Plot specs live in `task.yaml` alongside `default:` and `mode:` sections:

```yaml
# task.yaml
default:
  n_max_trials: 1500
  ...

plot:
  panels:
    - title: "Performance"
      type: rolling_mean
      field: correct
      window: 20
      x_label: "Trial"
      y_range: [0, 1]
    - title: "Reward total"
      type: cumulative_sum
      field: reward_volume_ul
      x_label: "Trial"
    - title: "Response latency"
      type: histogram
      field: response_latency_ms
      bins: 40
      x_label: "Latency (ms)"
```

**Supported panel types (implemented in `agent/plot.py`):**

| type | description |
|---|---|
| `rolling_mean` | rolling mean of `field` over `window` trials |
| `cumulative_sum` | cumulative sum of `field` |
| `timeseries` | raw `field` values per trial |
| `histogram` | histogram of `field` across all trials |
| `scatter` | `field_x` vs `field_y` |

Agent `plot.py` reads the spec and trial buffer, returns Plotly-ready JSON. ~150 lines. Tested independently of FastAPI.

If `plot:` key absent: `/session/plot` returns `{"panels": []}`. UI shows empty plot area. No task code changes needed.

---

## 5. Setup-agent port assignment

All setups run as virtual hardware on the same physical machine (same OS). Each setup-agent needs a unique port.

**Agent port in SetupConfig (or a new AgentConfig):**

```yaml
# setup-1.yaml
name: setup-1
agent_port: 8765
devices:
  bpod: ...
```

Default: `agent_port: 8765`. Each additional setup increments by 1 (8766, 8767, ...).

`msw agent start --setup setup-1` reads `agent_port` from `SetupConfig`, starts uvicorn on that port.

CLI `_find_agent()` order: (1) `MSW_AGENT_URL` env var, (2) `SetupConfig.agent_port` if setup known, (3) probe `localhost:8765`.

---

## 6. agents.json — unified static config

```json
[
  {
    "name": "setup-1",
    "agent_url": "http://192.168.100.101:8765",
    "cameras": [
      {"name": "top",    "stream_url": "http://192.168.100.111:8001/stream.mjpg"},
      {"name": "left",   "stream_url": "http://192.168.100.112:8001/stream.mjpg"},
      {"name": "right",  "stream_url": "http://192.168.100.113:8001/stream.mjpg"},
      {"name": "bottom", "stream_url": "http://192.168.100.114:8001/stream.mjpg"}
    ]
  },
  {
    "name": "setup-2",
    "agent_url": "http://192.168.100.101:8766",
    "cameras": [
      {"name": "top",    "stream_url": "http://192.168.100.121:8001/stream.mjpg"},
      ...
    ]
  }
]
```

When central server is added (Stage 3), `agents.json` becomes `GET /registry/rigs` → same shape, one-line change in the Pinia store.

HTTP vs HTTPS: `agent_url` is a full URL. If Traefik is in front, the URL changes to `https://...`. No code change in the Vue app — it uses the URL as-is. No hardcoded protocol assumptions anywhere.

---

## 7. Agent API endpoints (Stage 1 complete list)

### Hardware

| Method | Path | Notes |
|---|---|---|
| `GET` | `/hardware/status` | `{bpod_connected, stage_connected, setup_name}` |
| `POST` | `/hardware/connect` | `{setup: str}` |
| `POST` | `/hardware/disconnect` | graceful |
| `POST` | `/hardware/action` | `ActionRequest` → BpodOverrideAPI |

### Session

| Method | Path | Notes |
|---|---|---|
| `GET` | `/session/status` | `SessionStatus` (state, subject, task, trial_count, reward_count, elapsed_s) |
| `POST` | `/session/start` | `SessionStartRequest` → creates event_queue, starts TaskProcess thread |
| `POST` | `/session/stop` | sets `TaskRunner.continue_task = False` |
| `GET` | `/session/plot-spec` | task's `plot:` YAML → Plotly layout skeleton; `{}` when idle |
| `GET` | `/session/plot?since_trial=N` | incremental Plotly trace updates from trial N |

### Config

| Method | Path | Notes |
|---|---|---|
| `GET` | `/config/subjects` | `list[str]` from config_dir |
| `GET` | `/config/tasks` | `list[str]` |
| `GET` | `/config/task-modes/{task}` | `list[str]` from task.yaml |
| `GET` | `/config/setup` | `SetupConfig` serialised |

All endpoints: CORS headers enabled (`allow_origins=["*"]` for LAN deployment). HTTP Basic auth gated by `MSW_AGENT_PASSWORD` env var (empty = no auth, for local dev). TLS via Traefik when deployed.

---

## 8. msw-ui Vue/TS project (external/msw-ui)

### Stack

| Layer | Choice | Notes |
|---|---|---|
| Framework | Vue 3 + TypeScript | Composition API, `<script setup>` |
| Build | Vite | HMR in dev, optimised production bundle |
| State | Pinia | per-setup store, localStorage persistence |
| Routing | Vue Router | hash mode (`#setup-1`) for file:// compatibility |
| Plotting | Plotly.js | `plotly.js-dist-min` (3 MB) or `plotly.js-basic-dist` (1 MB) |
| Linting | ESLint + `eslint-plugin-vue` + `@typescript-eslint` | |
| Formatting | Prettier | |
| Git hooks | `husky` + `lint-staged` | |
| Versioning | `commitizen` + `standard-version` | same pattern as other repos |

### Layout

```
Tab bar: setup-1 | setup-2 | npxb | ...  (#hash navigation)

Per-setup tab:
┌─────────────────────────────────────────────────────────────────┐
│ [state badge]  subject · task · mode          [Start ▼] [Stop] │
├─────────────────────────────────────────────────────────────────┤
│  Camera grid (2×2 or 1×4, MJPEG, N/A overlay, lazy per tab)   │
├─────────────────────────────────────────────────────────────────┤
│  Trials: 142  Rewards: 38  Total: 3.8 ml  Elapsed: 23:14       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─ Performance ──┐  ┌─ Reward total ─┐  ┌─ Latency ─────┐    │
│  │  Plotly chart  │  │  Plotly chart  │  │  Plotly chart  │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│  [Override]  Valve 1 [Pulse 50ms] [Flush]  Valve 2 [Pulse] ... │
└─────────────────────────────────────────────────────────────────┘
```

### Component tree

```
App.vue
  TabBar.vue          — tab buttons, hash navigation
  SetupPanel.vue      — per-setup panel (one rendered at a time)
    SessionHeader.vue — state badge, subject/task/mode dropdowns, start/stop
    CameraGrid.vue    — MJPEG streams, lazy init on tab activate
    SessionMetrics.vue — trial/reward/elapsed counters
    PlotGrid.vue      — Plotly panel grid, empty when idle
      PlotPanel.vue   — single Plotly div, extendTraces for incremental updates
    OverridePanel.vue — BpodOverride valve buttons, calls POST /hardware/action
```

### Pinia store structure

```typescript
// stores/session.ts — one store per setup, keyed by name
interface SessionStore {
  state: "idle" | "running" | "stopping" | "error" | "offline"
  subject: string | null
  task: string | null
  trial_count: number
  reward_count: number
  reward_total_ul: number
  elapsed_s: number
  last_polled_trial: number       // cursor for incremental /session/plot
  plot_traces: PlotTraceStore[]   // accumulated Plotly trace data
  plot_spec: PlotSpec | null      // loaded once per session
}
// Persisted to localStorage: msw_session_<name>
// Cleared when session_id changes or state goes idle after running
```

### Camera stream handling

Identical logic to test-gen page:
- MJPEG `<img>` with `data-src` attribute
- `initStream()` composable: `fetch()` probe every 5 s, N/A overlay on failure, auto-reconnect
- Tab switch: `img._stopStream()` on deactivate, `initStream()` on activate
- `@hashchange` event + Vue Router's `beforeEach` hook triggers mount/unmount

### GitHub Actions (`.github/workflows/`)

```
ci.yaml         — on push/PR: install, lint, typecheck, build
bump.yaml       — manual: bump version, tag, push
```

---

## 9. Blockout window timing — all tasks

The pattern to add to every task `run()` loop:

```python
# REMOVE: logging.info(f"Trial: {trial_index}")  # at loop top
# ADD: after run_state_machine() returns
_t_bpod_done = time.perf_counter()

trial_data = ...
task_control.update(...)
task_control.save()

_compute_ms = (time.perf_counter() - _t_bpod_done) * 1000
logging.info(
    f"Trial {trial_index:4d}: {task_control.last_outcome or 'barcode':<9} | "
    f"compute {_compute_ms:.0f}ms"
)
```

The compute window covers: trial data extraction, outcome update, level progression, JSONL save, SMA construction. It does NOT include ITI sleep (intentional — we want to know Python compute time, not wait time).

Done in: `tasks/sequence/sequence.py` ✓
Pending: all other tasks (probabilistic_switching, fixedsubjects, airpuff, optotagging, etc.)

---

## 10. Implementation sequence

### Phase 0 — already done
- [x] `BpodOverrideAPI` class (`hardware/bpod/override.py`)
- [x] Float rounding in `_NumpyEncoder` (`logic/io.py`)
- [x] Blockout timing in sequence task

### Phase 1 — Stage 1 agent core
1. `agent/session_manager.py` — event queue, drain thread, trial buffer, counters
2. `agent/plot.py` — PlotSpec loader + Plotly trace computation (rolling_mean, cumulative_sum, histogram, timeseries)
3. `agent/hardware_manager.py` — Bpod/stage handle ownership, BpodOverrideAPI wrapper
4. `agent/routers/session.py` — /session/* endpoints
5. `agent/routers/hardware.py` — /hardware/* endpoints
6. `agent/routers/config.py` — /config/* endpoints
7. `agent/app.py` — FastAPI + uvicorn entrypoint, CORS, lifespan
8. `msw agent {start,stop,status}` CLI subcommand
9. `agent_port` field in SetupConfig
10. `TaskProcess.__init__` accepts `event_queue=None`
11. Tests: mock hardware, state transitions idle→running→idle→error

### Phase 2 — Vue UI scaffold
1. Create `external/msw-ui/` with Vite + Vue 3 + TS
2. `agents.json` with all setups + camera URLs
3. `SessionStore` (Pinia) with localStorage persistence
4. `useAgentPolling` composable (status + plot polling, retry on failure)
5. `CameraGrid.vue` (MJPEG stream, port from test-gen page)
6. `PlotPanel.vue` (Plotly.js, `extendTraces` for incremental)
7. `SessionHeader.vue` (start/stop, subject/task dropdowns from /config/*)
8. `OverridePanel.vue` (valve buttons → POST /hardware/action)

### Phase 3 — Stage 2 CLI dispatch
- `_find_agent()` + `_dispatch_to_agent()` in `execute.py`
- `--no-agent` flag

### Phase 4 — Stage 3 central server (optional for multi-network)
- `central/registry.py` + heartbeat
- `central/proxy.py` HTTP forwarding
- Vue: replace `agents.json` with `GET /registry/rigs` (one-line store change)

### Phase 5 — Stage 6 interactive mode
- SSE endpoint `/session/events` for live trial counter (no full WS needed)
- `BpodOverrideAPI` wired into `HardwareManager` for concurrent-session valve control

---

## 11. Session history in UI

The Pinia store maintains a per-setup ring buffer of the last `SESSION_HISTORY_MAX = 20` completed sessions (persisted to `localStorage`). An entry is written automatically when the status transitions from `running/stopping → idle`. Entries from excluded task prefixes (`_calibration_`, `_test_`, `example`) are dropped.

Each history entry: `session_id, subject, task, task_mode, started_at, ended_at, trial_count, reward_count, reward_total_ul`.

The `SessionHistory.vue` component is collapsed by default, expanding to a sortable table on click. No external storage needed — the last 20 sessions per setup persist in `localStorage` until the user clears browser data.

**Plot clear / history navigation:**

- **Clear** button in the plot section header calls `store.clearPlots(name)` — resets accumulated trace arrays to empty, resets `lastPolledTrial` to 0. Next poll refetches from trial 0. Useful when something went wrong with the incremental accumulation.
- Previous sessions are not replayed in the online plot (there is no endpoint to query historical trial data for plotting). They appear only in the summary history table.
- If the user wants to browse historical plots, that is a future "session replay" feature (v2 scope).

---

## 12. Open questions

- **Blockout timing in other tasks**: add pattern task by task; define a `log_trial_timing()` helper in `TaskRunner` to standardise the log format.
- **plot.py computation time**: if a large trial buffer + complex aggregation causes > 20 ms API response, move computation to a background thread via `asyncio.to_thread()`.
- **Plot spec versioning**: if task.yaml `plot:` block changes mid-development, the localStorage-persisted traces may have wrong shape. Mitigate by including `plot_spec_hash` in the store and clearing traces on mismatch.
- **OverridePanel during session**: `POST /hardware/action` must go through `HardwareManager._write_lock` (already implemented in `BpodOverrideAPI`). Confirm lock is acquired by agent before forwarding to task-injected bpod.
- **Camera URLs in central server context**: if central server proxies camera streams, add `camera_proxy_url` to `RigEntry`. For direct-agent mode (agents.json), camera URLs are per-setup in `agents.json` — no proxy needed.
