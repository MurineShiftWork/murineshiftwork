# LogAgent + Central UI — Architecture Plan

*Created 2026-05-23. Branch: ft/monitor-step1 (refactor from TrialRelay design).*
*Supersedes: PLAN_msw_monitor.md, PLAN_msw_ui_agent_broadcast.md (agent/ path).*

---

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Session identity | UUID4 string | Namespace-independent; basename kept as human label only |
| Auth (ingest endpoints) | Bearer token in `Authorization` header | Token stored in `msw_machine.yaml` under `log_bearer_token`; `log_url` names the server |
| Auth (UI query endpoints) | None for v1 (LAN only) | Add if UI is exposed beyond LAN |
| Container topology | **Two containers** | UI container (Vue SPA only, nginx); API container (FastAPI, receives from LogAgent + serves query endpoints to UI) |
| LogAgent lifetime | One daemon Process per session | Created in `TaskProcess.__init__`, exits on None sentinel |
| LogAgent storage | None — pure forwarder | No local history; all state lives in API container |
| Trial payload | Two fields: `bpod_export` (raw) + `task_info` (processed) | Raw for alignment/replay; processed for plotting |
| Session start payload | Full `args_dict` (evaluated settings, paths, metadata) + `plot_spec` dict | Mirrors what TaskProcess writes to session YAML |
| Data paths | Two idempotent consumers of same data | Real-time → UI (LogAgent); retrospective → Labwatch (future import) |
| Buffer size (API container) | **UNRESOLVED** | How many sessions / trials to keep in memory; ring buffer vs. disk-backed |
| Historical sessions | Not in scope for v1 | API container is best-effort; restart clears state |
| CLI | No `msw monitor` subcommand | LogAgent starts automatically; UI container runs independently |

---

## Architecture

```
Setup machine (each rig)
  msw run (CLI process)
    └── TaskProcess.__init__
          ├── LogAgent.start()      daemon Process; exits when session ends
          └── TaskRunner (Thread)
                └── task loop: after each trial
                      try: relay_queue.put_nowait({bpod_export, task_info})
                      except queue.Full: pass   ← ~0 µs drop

LogAgent (multiprocessing.Process, daemon=True)
  ├── receives session_start from TaskProcess (via queue, first item)
  ├── POST /ingest/session/start   → API container
  ├── loop: queue.get(timeout=5)
  │     → POST /ingest/session/trial  → API container
  └── None sentinel → POST /ingest/session/stop → API container

API container  (FastAPI + uvicorn, port 8080)
  POST /ingest/session/start    ← LogAgent
  POST /ingest/session/trial    ← LogAgent
  POST /ingest/session/stop     ← LogAgent
  GET  /sessions                → Vue UI (list of active + recent sessions)
  GET  /sessions/{uuid}         → Vue UI (session metadata + status)
  GET  /sessions/{uuid}/trials?since=N  → Vue UI (incremental, Vue tracks cursor)
  GET  /sessions/{uuid}/plotspec → Vue UI
  GET  /health

UI container  (nginx, port 80/443)
  Serves pre-built Vue 3 + TS + Plotly.js dist/
  Vue polls API container at configured API_BASE_URL (env var in dist)
```

---

## Auth

Bearer token strategy:
- Token set once in `~/.murineshiftwork/msw_machine.yaml`:
  ```yaml
  log_url: http://monitor-host:8080
  log_bearer_token: <your-token-here>
  ```
- LogAgent reads `log_bearer_token` from machine config and sends `Authorization: Bearer <token>` on every ingest POST
- API container validates token on all `/ingest/` routes; query routes (`/sessions/...`) unprotected for v1
- If `log_bearer_token` is absent from machine config: ingest calls proceed without auth (dev mode)

**Future discussion: machine vs setup level config**
Currently `log_url` and `log_bearer_token` live at machine level (one server per physical rig).
This may be too coarse if a single machine runs multiple setups that report to different servers,
or if different setups need different auth tokens.
Decision deferred until we have >1 rig using this — revisit when multi-rig is in scope.

---

## Ingest payloads

**Design principle: LogAgent is hardware-blind.**
LogAgent does not know or care what hardware produced the trial data.
It forwards whatever the task puts in `trial_data` as an opaque dict.
The PlotSpec references field names — if a field is absent from `trial_data`
for a given task, that panel is silently empty. The task is solely responsible
for making its `trial_data` fields match its `plot_spec.yaml` field names.

### POST /ingest/session/start
```json
{
  "session_uuid": "uuid4-string",
  "setup": "rig-a",
  "subject": "mouse001",
  "task": "sequence",
  "started_at": "2026-05-23T09:00:00+00:00",
  "args_dict": { ... },
  "session_paths": { "session_folder": "...", "session_basename": "...", ... },
  "plot_spec": { ... } | null
}
```

`args_dict` is the full evaluated args dict the CLI process has at session start
(includes `settings.task.patched`, `session_paths`, metadata, etc.) — the same
data that goes into the session YAML. No hardware-specific keys are required.

### POST /ingest/session/trial
```json
{
  "session_uuid": "uuid4-string",
  "trial_index": 42,
  "trial_data": { ... }
}
```

`trial_data` is an opaque dict. Content is entirely task-defined.
LogAgent never reads, parses, or validates it.
PlotSpec `field:` references must match keys present in `trial_data`.

A typical sequence task `trial_data` looks like:
```json
{
  "trial_index": 42,
  "outcome": "correct",
  "level": 5,
  "reward_count_trial": 1,
  "liquid_ul_trial": 3.0,
  "liquid_ul_cumulative": 126.0,
  "trial_time_s": 1234.5
}
```
Whether to include raw hardware output (e.g. state machine timestamps) is the
task's choice. Including it makes the UI data richer but increases payload size.

### POST /ingest/session/stop
```json
{
  "session_uuid": "uuid4-string",
  "ended_at": "2026-05-23T10:30:00+00:00",
  "summary": { ... }
}
```

`summary` is also opaque — a flat dict of session-level counters the task
chooses to report (e.g. `trial_count`, `reward_count`, `liquid_ul`). The API
server stores it as-is; the Vue UI can display whatever keys it finds.

---

## API container state model

```python
@dataclass
class SessionRecord:
    uuid: str
    setup: str
    subject: str
    task: str
    state: Literal["running", "stopped"]
    started_at: str
    ended_at: str | None
    args_dict: dict
    session_paths: dict
    plot_spec: dict | None
    trials: deque  # maxlen: UNRESOLVED
```

Sessions stored in `dict[uuid, SessionRecord]`.
Ring buffer of session UUIDs for the `/sessions` list: **UNRESOLVED (size)**.

---

## Plot spec in session dir

At session start, `TaskProcess` (or LogAgent) copies the task's `plot_spec.yaml` into the session folder as `<session_basename>.plot_spec.yaml`. This enables:
- Historical re-plotting from the UI (load spec + load JSONL)
- Python analysis scripts that don't need the task source

---

## Docker

Two containers, one compose file:

```yaml
services:
  msw-ui:
    image: nginx:alpine
    volumes:
      - ./dist:/usr/share/nginx/html:ro
    ports: ["80:80"]

  msw-api:
    build: .
    command: uvicorn murineshiftwork.monitor.server:app --host 0.0.0.0 --port 8080
    ports: ["8080:8080"]
    environment:
      MSW_UI_BEARER_TOKEN: "${MSW_UI_BEARER_TOKEN}"
```

Vue `dist/` built separately (CI or `npm run build`). `API_BASE_URL` baked in at build time or injected via `window.__MSW_CONFIG__` at nginx serve time.

---

## Task-side contract for relay_queue

Each task that supports LogAgent must follow this pattern:

```python
# At end of each trial — ~1 µs, never blocks
_relay_q = self.input_kwargs.get("relay_queue")
if _relay_q is not None:
    try:
        _relay_q.put_nowait({
            "trial_index": ...,
            # any fields the task's plot_spec.yaml references:
            "outcome": ...,
            "level": ...,
            # etc.
        })
    except Exception:
        pass

# At session end (before kill_queue)
if _relay_q is not None:
    try:
        _relay_q.put_nowait({"__stop__": True, "summary": {...}})
    except Exception:
        pass
```

The `__stop__` sentinel carries the session-end summary dict.
LogAgent detects it, sends `POST /ingest/session/stop`, then exits.
No hardware-specific keys. The task is responsible for field naming.

---

## Hardware abstraction debt in TaskProcess

`TaskProcess.__init__` still has `serial_port_bpod` and `require_bpod` as
first-class parameters — Bpod-specific names that leak into the generic layer.

Target state (future branch, not this one):
- Remove `serial_port_bpod` parameter; port resolution lives entirely in
  `BpodDevice.preflight()` called by `HardwareManager`
- Rename `require_bpod` → `require_hardware` or remove it (hardware presence
  is implied by what's in `devices=`)
- `TaskProcess` receives hardware via `devices: dict` only; no serial port args

Until then: `serial_port_bpod` is legacy; callers using `HardwareManager` pass
`bpod=devices["bpod"]` and `serial_port_bpod` stays empty. Both paths coexist.

---

## Implementation order

### ft/monitor-step1 (done)
- [x] Rename `TrialRelay` → `LogAgent`; package `monitor/` → `logagent/`; three-phase lifecycle
- [x] Session UUID: generate in `TaskProcess.__init__`, store in session YAML, tag all LogAgent payloads
- [x] Trial payload: task puts opaque `trial_data` dict; `__stop__` sentinel carries summary
- [x] Bearer token: read `log_bearer_token` from `msw_machine.yaml`; inject into LogAgent HTTP headers; validate on ingest endpoints
- [x] Plot spec: copy `{task}/plot_spec.yaml` → `{session_file_path}.msw.plot_spec.yaml` in `init_task()` if file exists
- [x] Remove `msw monitor` CLI subcommands (server is started externally, not via CLI)
- [x] `fastapi`, `httpx`, `uvicorn` added to dev extras
- [x] Tests: 30 passing — LogAgent lifecycle, auth, UUID, server ingest, TaskProcess integration

### ft/monitor-step2 (after step1 validated on rig)
- [ ] `GET /sessions/{uuid}/trials?since=N` — incremental trial query endpoint on the log_url API server
  (UI polls this to get only new trials since last fetch; Vue tracks cursor N locally)
  **Direction: UI → log_url backend API, not UI → CLI**
- [ ] `msw plotspec <task>` — load + print PlotSpec YAML; `--dry-run` generates synthetic data
- [ ] Verify LogAgent `trial_data` field names for sequence and fixedsubjects tasks

### ft/monitor-step3 (Docker + Vue)
- [ ] `Dockerfile.monitor` + `docker-compose.monitor.yml` — two containers: nginx (Vue dist) + FastAPI (API)
- [ ] Vue UI wiring — polls `/session/status` + `trials?since=N`; PlotSpec-driven Plotly panels

---

## Open questions

- **Buffer size**: How many sessions and trials to keep in API container memory? Disk-backed option?
- **API_BASE_URL injection**: Bake into Vue dist at build time (simpler) or inject via nginx at serve time (more flexible)?
- **Multi-rig ingest ordering**: If two rigs POST simultaneously, ordering of `/sessions` list — by `started_at` desc.
- **Reconnect on LogAgent crash**: If LogAgent subprocess dies mid-session, do we restart it, or accept the data gap?
