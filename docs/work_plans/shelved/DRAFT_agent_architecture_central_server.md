# MSW Agent Architecture — Central Server Design (SHELVED)

> **Shelved 2026-05-20.** Superseded by `PLAN_msw_ui_agent_broadcast.md`.
> Key difference: this doc has a central server + proxy between agents and the Vue UI.
> The decided design has no central server — `agents.json` static config, polling transport,
> Vue SPA in `external/msw-ui/` served per-machine. Kept for reference if a
> central server / multi-machine aggregation is needed in future.
>
> Original status: design complete 2026-05-18. Implementation not started.
> Frontend: **Vue 3 + TypeScript** (decided). Backend: FastAPI. No React.

---

## Target architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser  —  Vue 3 / TypeScript SPA                        │
│   rig cards | session control | live trial counters         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│  Central server  —  FastAPI                                 │
│   registry | proxy | WS multiplexer | session history       │
└────┬──────────────────────────────────────────┬─────────────┘
     │ HTTP + WS  (per rig)                     │
┌────▼──────────────┐                  ┌────────▼──────────────┐
│  Setup-agent      │                  │  Setup-agent          │
│  rig-1  :8765     │  ...             │  rig-N  :8765         │
│  FastAPI          │                  │  FastAPI              │
│  HardwareManager  │                  │  HardwareManager      │
│  SessionManager   │                  │  SessionManager       │
└────┬──────────────┘                  └────────┬──────────────┘
     │ inject bpod=, stage=                     │
┌────▼──────────────┐                  ┌────────▼──────────────┐
│  TaskProcess      │                  │  TaskProcess          │
│  TaskRunner(thd)  │                  │  TaskRunner(thd)      │
└───────────────────┘                  └───────────────────────┘

CLI path (no central server needed):
  msw run → _find_agent() → POST localhost:8765/session/start
                          → fallback: direct TaskProcess (existing)
```

---

## Setup-agent API

Port `8765` by default. One process per rig machine, launched with `msw agent start --setup <name>`.

### Hardware endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/hardware/status` | `{bpod_connected, stage_connected, setup_name}` |
| `POST` | `/hardware/connect` | `{setup: str}` — opens Bpod + stage |
| `POST` | `/hardware/disconnect` | closes handles gracefully |
| `POST` | `/hardware/action` | `ActionRequest` (existing model) |

### Session endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/session/status` | `SessionStatus` |
| `POST` | `/session/start` | `SessionStartRequest` → `{session_id, session_folder}` |
| `POST` | `/session/stop` | graceful stop |
| `WebSocket` | `/session/events` | stream `TrialEvent` objects |

### Config endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/config/subjects` | `list[str]` from config_dir |
| `GET` | `/config/tasks` | `list[str]` |
| `GET` | `/config/setup` | `SetupConfig` serialised |

### New Pydantic models (add to `logic/config/models.py`)

```python
class SessionStartRequest(BaseModel):
    subject: str
    task: str
    task_mode: str = ""
    task_settings_overrides: list[str] = []   # KEY=VALUE same as CLI
    experimenter: str = ""
    simulate: bool = False

class SessionStatus(BaseModel):
    state: Literal["idle", "running", "stopping", "error"]
    session_id: str | None
    session_folder: str | None
    subject: str | None
    task: str | None
    trial_count: int
    reward_count: int
    started_at: str | None   # ISO8601
    error: str | None

class TrialEvent(BaseModel):
    event: Literal["session_start","trial_start","trial_end","reward","session_end","error"]
    rig_name: str
    trial_index: int
    timestamp: float
    reward_count: int
    extra: dict[str, Any] = {}
```

---

## Central server API

Thin proxy + rig registry. Deployable on lab server or same machine.

### Registry (agents call in)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/registry/register` | `{rig_name, agent_url, setup_name}` |
| `POST` | `/registry/heartbeat` | `{rig_name}` — agents call every 30 s |
| `GET` | `/registry/rigs` | `list[RigEntry]` — offline if >90 s since last heartbeat |

### Proxy (web UI / CLI call these)

| Method | Path | Notes |
|---|---|---|
| `GET` | `/rigs/{rig}/session/status` | forward to agent, cache 2 s |
| `POST` | `/rigs/{rig}/session/start` | forward `SessionStartRequest` |
| `POST` | `/rigs/{rig}/session/stop` | forward |
| `WebSocket` | `/rigs/{rig}/session/events` | open client WS to agent, inject `rig_name`, multiplex |
| `POST` | `/rigs/{rig}/hardware/action` | forward `ActionRequest` |
| `GET` | `/rigs/{rig}/sessions` | scan data_dir YAML files for history |

---

## Hardware handle lifetime

- Bpod: **stays connected across sessions** — agent holds handle, injects `bpod=` into `TaskProcess`. Closed only on `/hardware/disconnect` or fatal serial error.
- Stage: may reconnect per session (~200 ms) or stay connected — agent's choice.
- `TaskProcess.exit_safely()` does NOT close the connection when running under agent — only calls `bpod.stop_trial()`.

---

## CLI migration (`execute.py` + `__init__.py`)

```python
# execute.py additions
def _find_agent(args_dict) -> str | None:
    """Check MSW_AGENT_URL env var, then probe localhost:8765."""

def _dispatch_to_agent(agent_url, args_dict) -> None:
    """POST SessionStartRequest, poll status until idle."""

def run_task(**args_dict):
    agent_url = None if args_dict.get("no_agent") else _find_agent(args_dict)
    if agent_url:
        _dispatch_to_agent(agent_url, args_dict)
    else:
        _run_task_direct(**args_dict)   # existing logic unchanged
```

New flag: `msw run --no-agent` to always bypass.
New subcommand: `msw agent {start,stop,status}`.

---

## Vue 3 / TypeScript frontend

Project: separate repo or `src/murineshiftwork/central/frontend/`.
Stack: **Vue 3 + TypeScript + Vite**. No React. Served as static files by the central server FastAPI (`StaticFiles`).

### Minimum viable UI

- **Rig cards grid** — one card per registered rig: setup name, state badge (idle/running/error), subject + task labels, trial count, reward count, elapsed time.
- **Session control** — per-card Start (subject picker, task picker, mode dropdown) and Stop buttons.
- **Live updates** — WebSocket to `/rigs/{rig}/session/events`; Vue reactive store updated per event.
- **Auth** — HTTP Basic prompt on load; stored in `localStorage` for session.

### Deferred to v2

Real-time performance plots, session replay timeline, drag-and-drop protocol builder, user management, multi-rig sync, mobile layout.

---

## New source tree

```
src/murineshiftwork/
    agent/
        app.py               # FastAPI instance, lifespan hooks
        hardware_manager.py  # Bpod + stage handle ownership
        session_manager.py   # TaskProcess lifecycle, TrialEvent queue
        routers/
            hardware.py
            session.py
            config.py

    central/
        app.py               # FastAPI proxy + static file serving
        registry.py          # RigRegistry with heartbeat tracking
        proxy.py             # HTTP + WS forwarding

    # existing — minimal changes:
    cli/
        execute.py           # add _find_agent, _dispatch_to_agent
        parser.py            # add msw agent subcommand
    logic/config/models.py   # add SessionStartRequest, SessionStatus, TrialEvent
```

---

## Implementation stages

### Stage 1 — Setup-agent core (no web UI)
- `agent/hardware_manager.py`: hold Bpod/stage across sessions, expose connect/disconnect/action
- `agent/session_manager.py`: wrap TaskProcess, TrialEvent queue, state machine
- `agent/routers/`: hardware, session, config endpoints
- `agent/app.py`: FastAPI + uvicorn entrypoint
- `msw agent start` CLI subcommand
- Tests: mock hardware, test state transitions idle→running→idle→error

### Stage 2 — CLI dispatch
- `execute._find_agent()` + `_dispatch_to_agent()` in `execute.py`
- `--no-agent` flag
- Integration test: `msw run` against a local agent process (SimBpod)

### Stage 3 — Central server registry + proxy
- `central/registry.py` with heartbeat expiry
- `central/proxy.py` HTTP + WebSocket forwarding
- `msw central start` CLI subcommand

### Stage 4 — Vue/TS frontend
- Vite project scaffold in `central/frontend/`
- Rig card components, WebSocket composable, Pinia store
- FastAPI serves `dist/` as `StaticFiles`

### Stage 5 — Auth + hardening
- HTTP Basic on agent, central stores credentials per rig
- Graceful shutdown, handle Bpod serial error → reconnect path
- Logging, health check endpoint

---

## Auth

HTTP Basic per rig (`MSW_AGENT_PASSWORD` env var). Central server stores per-rig credentials in its config YAML and re-authenticates when proxying. Add nginx TLS terminator if exposed beyond lab LAN — outside MSW scope.

## Session history

No database. Central server scans `data_dir` for `.msw.session.yaml` files to serve history (`GET /rigs/{rig}/sessions`). Source of truth remains the YAML files written by `TaskProcess`.

## v1 non-scope

No database, no mDNS discovery, no live plots in web UI, no Windows agent, no multi-rig sync, no automatic proxy failover.
