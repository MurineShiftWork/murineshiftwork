# MSW Monitor — CLI→UI Data Pipeline

> **SUPERSEDED by `MASTER_PLAN.md` §5 (2026-05-22).**
> Content preserved for reference; `MASTER_PLAN.md` is authoritative.
> CLI is primary; monitor is best-effort infrastructure.

---

## Decision: CLI-primary, no agent hardware ownership

| Principle | Implication |
|---|---|
| `msw run` starts all sessions | Agent/monitor can never start a session |
| Data durability is in-process | Monitor being down never affects a session |
| Network never blocks task loop | All outbound sends are fire-and-forget, non-blocking |
| Monitor is read-only | Vue UI shows live plots, no control actions in v1 |

The `agent/` package (Stage 1, `98ed977`) is superseded. Strip it after monitor is validated.

---

## Naming

| Name | Role |
|---|---|
| `msw monitor` | CLI command to start the monitor server |
| `murineshiftwork.monitor` | Python package — server + relay |
| `murineshiftwork.monitor.server` | FastAPI server (runs in Docker) |
| `murineshiftwork.monitor.relay` | `TrialRelay` sidecar process — pushes from task to server |
| `TrialRelay` | The `multiprocessing.Process` subclass started by `TaskProcess` |
| `msw plotspec <task>` | CLI debug tool — prints PlotSpec for a task |

---

## Architecture

```
msw run (CLI process)
  └── TaskProcess.__init__
        ├── TrialRelay.start()        daemon process, reads from mp.Queue
        └── TaskRunner (Thread)
              └── task loop
                    └── after save_trial_data():
                          queue.put_nowait(raw_trial_dict)  ← ~1 µs, never blocks

TrialRelay (multiprocessing.Process, daemon)
  └── reads raw_trial_dict from queue
  └── HTTP POST /ingest/{setup}  →  monitor server
        ├── failure: log DEBUG, drop event (never retries, never blocks)
        └── timeout: 0.5 s

msw monitor serve  (FastAPI, Docker, port 8080)
  ├── POST /ingest/{setup}/start    — session start: {task, subject, setup, plot_spec}
  ├── POST /ingest/{setup}/trial    — per-trial: raw trial dict
  ├── POST /ingest/{setup}/stop     — session end
  ├── GET  /session/status/{setup}  — {state, trial_count, reward_count, elapsed_s}
  ├── GET  /session/plot/{setup}?since_trial=N  — PlotSpec panel updates
  └── WS   /events/{setup}          — push notification on trial complete

Vue UI (served from same container, port 8080/ui)
  └── polls /session/status every 2 s
  └── polls /session/plot every 5 s (when session running)
  └── subscribes to WS /events for immediate trial notification
```

---

## Non-blocking guarantee

The task loop must never slow down because of data sending:

```
Task loop (hot path)             TrialRelay (daemon process)
─────────────────────────        ──────────────────────────
save_trial_data()                while True:
                                     raw = q.get(block=True)
try:                                 try:
    q.put_nowait(raw_dict)               _http_post(raw, timeout=0.5)
except queue.Full:                   except Exception:
    pass   ← ~0 µs                       logging.debug(...)
                                     # never propagates to task
```

- `queue = multiprocessing.Queue(maxsize=500)` — holds ~500 buffered trials if monitor is slow
- `put_nowait` is a single lock+check, takes ~1 µs regardless of network state
- TrialRelay crash → daemon=True means no zombie; task continues unaffected
- Monitor down → HTTP POST times out in 0.5 s, caught silently in TrialRelay

---

## PlotSpec

Defined in `task.yaml` alongside `default:` and `mode:` blocks:

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

PlotSpec is sent once at session start (`POST /ingest/{setup}/start`). Monitor stores it and uses it to compute panel updates from the trial buffer on every `GET /session/plot` request.

Panel types: `rolling_mean`, `cumulative_sum`, `timeseries`, `histogram`, `scatter`.

Computation lives in `monitor/server.py` — reads from `trial_buffer` (deque), returns `{since_trial, last_trial, panels: [{title, x_append, y_append}]}`. Vue client appends via `Plotly.extendTraces()`.

---

## Debugging PlotSpec

```bash
# Print the plot: block from a task's task.yaml
msw plotspec sequence
msw plotspec probabilistic_switching_fixedsubjects

# Dry-run: simulate trial data and print computed panel updates
msw plotspec sequence --dry-run --n-trials 30

# Dump monitor's current state (live debug)
curl http://localhost:8080/debug/session/npxb | jq .
```

`msw plotspec` just loads `task.yaml` from the bundled or overlaid config and pretty-prints the `plot:` block as YAML. `--dry-run` generates synthetic trial data and runs it through the PlotSpec computation to show what `x_append`/`y_append` would look like.

---

## TrialRelay — implementation sketch

```python
# murineshiftwork/monitor/relay.py
import multiprocessing
import logging
import json
import urllib.request

class TrialRelay(multiprocessing.Process):
    def __init__(self, queue: multiprocessing.Queue, monitor_url: str, setup: str):
        super().__init__(daemon=True)
        self._queue = queue
        self._monitor_url = monitor_url.rstrip("/")
        self._setup = setup

    def run(self):
        while True:
            try:
                event = self._queue.get(block=True, timeout=5)
                if event is None:           # sentinel → shutdown
                    break
                self._post("trial", event)
            except Exception:
                pass                        # never propagates

    def _post(self, endpoint: str, payload: dict):
        url = f"{self._monitor_url}/ingest/{self._setup}/{endpoint}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=0.5)
        except Exception as exc:
            logging.debug("TrialRelay POST failed (%s): %s", endpoint, exc)
```

`TaskProcess` wires this up:
```python
# in TaskProcess.__init__, after session_paths is set:
self._relay_queue = None
self._relay_proc = None
monitor_url = read_machine_config().get("monitor_url", "")
if monitor_url:
    self._relay_queue = multiprocessing.Queue(maxsize=500)
    self._relay_proc = TrialRelay(self._relay_queue, monitor_url, setup=self.setup)
    self._relay_proc.start()
    # POST session start event (includes plot_spec)
```

Tasks use:
```python
if self._relay_queue is not None:
    try:
        self._relay_queue.put_nowait({
            "trial_index": trial_index,
            "correct": correct,
            "reward_delivered": reward_delivered,
            "reward_volume_ul": reward_volume_ul,
            "timestamp": time.monotonic(),
        })
    except queue.Full:
        pass
```

---

## Monitor server (Docker)

```dockerfile
# Dockerfile.monitor
FROM python:3.12-slim
COPY . /app
RUN pip install /app[monitor]
COPY external/msw-ui/dist /app/ui_dist
EXPOSE 8080
CMD ["msw", "monitor", "serve", "--port", "8080"]
```

```yaml
# docker-compose.monitor.yml
services:
  msw-monitor:
    build:
      context: .
      dockerfile: Dockerfile.monitor
    ports:
      - "8080:8080"
    volumes:
      - /mnt/maindata/msw_configs:/configs:ro
    environment:
      - MSW_CONFIG_DIR=/configs
    restart: unless-stopped
```

Start once per machine, covers all setups:
```bash
docker compose -f docker-compose.monitor.yml up -d
```

`msw_machine.yaml` entry:
```yaml
monitor_url: http://localhost:8080
```

If `monitor_url` is absent, TrialRelay is not started and no data is sent.

---

## Session start/stop events

At session start (`TaskProcess.__init__`):
```python
POST /ingest/{setup}/start
{
  "setup": "npxb",
  "subject": "AA001",
  "task": "sequence",
  "session_folder": "/mnt/maindata/data/AA001/...",
  "datetime": "2026-05-22T10:00:00",
  "plot_spec": {<parsed task.yaml plot: block>}
}
```

At session end (`TaskProcess.__exit__`):
```python
POST /ingest/{setup}/stop
{"n_trials": 150, "reward_count": 110, "session_water_ul": 330.0}
```

---

## Monitor endpoints (MVP)

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest/{setup}/start` | Session start + PlotSpec |
| `POST` | `/ingest/{setup}/trial` | Per-trial raw dict |
| `POST` | `/ingest/{setup}/stop` | Session end summary |
| `GET` | `/session/status/{setup}` | Live counters + state |
| `GET` | `/session/plot/{setup}` | PlotSpec panel updates (`?since_trial=N`) |
| `WS` | `/events/{setup}` | Push per-trial notification |
| `GET` | `/config/setups` | List setup names from agents.json |
| `GET` | `/debug/session/{setup}` | Full current state (debug) |

---

## Implementation order

1. **`monitor/server.py`** — FastAPI with in-memory state per setup (`SessionState`, `trial_buffer`, plot computation)
2. **`monitor/relay.py`** — `TrialRelay` Process (sketch above, ~80 lines)
3. **`TaskProcess` wiring** — read `monitor_url`, start `TrialRelay`, wire queue to tasks
4. **`msw monitor`** CLI subcommand — `serve`, `status`, `debug`
5. **`msw plotspec`** CLI subcommand — load + print + `--dry-run`
6. **Dockerfile.monitor** + `docker-compose.monitor.yml`
7. **Vue UI** wiring — point polling at `/session/status` and `/session/plot`
8. **Strip `agent/` package** — after monitor validated on one rig

---

## Open questions

1. **Per-trial dict schema**: which fields are mandatory across all tasks? `trial_index` and `timestamp` always; `correct`, `reward_delivered`, `reward_volume_ul` for plot panels — tasks that don't have these fields skip those panels.

2. **`agents.json` vs `monitor_url`**: keep `agents.json` for per-setup camera URLs; `monitor_url` in `msw_machine.yaml` for the single monitor server per machine.

3. **Auth**: no auth for v1 (monitor is LAN-only). Add HTTP Basic if exposed beyond LAN.

4. **Vue delivery**: serve Vue dist from FastAPI `StaticFiles`; no separate nginx needed in v1.

5. **Session history**: ring-buffer in monitor server (20 sessions per setup); no localStorage needed. Vue reads `/session/history/{setup}`.
