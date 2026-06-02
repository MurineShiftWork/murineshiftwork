# MSW Agent + UI: Architecture and Design Decisions

> Status: design locked 2026-05-19. Implementation detail and stage breakdown in `IMPLEMENTATION_PLAN.md`.
> Stage 1 built — commit `98ed977`.

---

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| UI framework | Vue 3 + TS + Plotly.js | SPA, no build step on rig machines (serve pre-built dist) |
| Server topology | No central server for v1 | `agents.json` static config lists agent URLs per setup |
| Transport (v1) | HTTP polling (2 s / 5 s) | Simpler than WS, sufficient for trial-rate data |
| Session history | Option A: localStorage ring-buffer (20 entries) | No backend history endpoint needed |
| PyQt `online_plotting` | Keep; add deprecation TODO comment | Not removed until msw-ui validated in production |
| Auth | HTTP Basic, `MSW_AGENT_PASSWORD` env var per rig | nginx TLS terminator if exposed beyond LAN |
| Plot data ownership | `plot:` block in `task.yaml` (PlotSpec) | Task owns its own plot definition; agent computes traces from trial buffer |

---

## Architecture

```
agents.json  (in config_dir alongside subjects/ setups/)
  [{name, agent_url, cameras:[{name, stream_url}]}, ...]

external/msw-ui/  (Vue 3 + TS + Plotly.js, pre-built dist)
  Tab bar: setup-1 | setup-2 | ...
  Per-tab: SessionHeader | CameraGrid | PlotGrid | OverridePanel
    ↕ GET /session/status every 2 s
    ↕ GET /session/plot?since_trial=N every 5 s (when running)

  Setup-agent  (FastAPI, port from SetupConfig.agent_port, default 8765)
    /hardware/status | reconnect | action
    /session/active | start | stop | plot-spec | plot | events (WS)
    /config/subjects | tasks | task-modes/{task} | setup | setups
    SessionManager: trial_buffer (deque), drain Thread
      ↑ queue.Queue.put_nowait() — fire-and-forget from task loop
    TaskProcess → TaskRunner(Thread) → Bpod state machine
```

No central server or proxy. CLI remains primary interface; web UI is read-only monitoring layer.

---

## PlotSpec (task.yaml `plot:` block)

Each task defines its own plot panels alongside `default:` and `mode:` blocks:

```yaml
# task.yaml
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

`agent/plot.py` loads the spec and computes incremental Plotly trace updates from the `trial_buffer`.
`GET /session/plot?since_trial=N` returns `{since_trial, last_trial, panels:[{title, x_append, y_append}]}`.
Vue client appends via `Plotly.extendTraces()`.

---

## Event queue (task → agent)

Non-blocking fire-and-forget after each trial:

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

Task code never imports from `agent/`. Queue injected by `SessionManager` at session start.

---

## Stage status

| Stage | Description | Status |
|---|---|---|
| 1 | Read-only endpoints, hardware persistence, HTTP Basic auth | **DONE** `98ed977` |
| 2 | Event queue bridge, live counters, `msw agent stop/status` | **NEXT** |
| 3 | PlotSpec in `task.yaml`, `agent/plot.py`, `/session/plot` | Planned |
| 4 | `POST /hardware/action` via `BpodOverrideAPI` | Planned |
| 5 | Session history (Option A localStorage) | Planned |
| 6 | PyQt `online_plotting.py` deprecation markers | Planned |
| Later | `msw ui` CLI, CLI dispatch (`_find_agent`), camera, namespace split | Blocked on above |

Full stage detail: `IMPLEMENTATION_PLAN.md`.

---

## Namespace split (last stage)

Package prefix: **`msw-tasks-`** for all task groups. Extract after agent sprint stable.
Full split plan in `IMPLEMENTATION_PLAN.md §4`.

| pip name | Contents | Status |
|---|---|---|
| `msw-tasks-core` | Calibration + test tasks | In monolith |
| `msw-tasks-sequence` | Sequence learning task | In monolith |
| `msw-tasks-switching` | PS freely moving + head-fixed | In monolith |
| `msw-tasks-other` | Airpuff, opto, homecage, openfield, … | In monolith |
| `msw-logic` | Logic + hardware layer | In monolith |
| `msw-agent` | FastAPI setup-agent | In monolith — Stage 1 done |
| `msw-readers` | Session data readers | In monolith |
| `msw-ui` | Vue SPA | Scaffold done (`external/msw-ui/`) |
| `murineshiftwork` | Meta-package with extras groups | Blocked on above |

PEP 420 namespace root ready (`murineshiftwork/__init__.py` removed).
Each extracted package ships its own `docs/` subtree; until split, docs live in `docs/tasks/` here.
