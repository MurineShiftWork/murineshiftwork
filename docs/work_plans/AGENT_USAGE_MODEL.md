# MSW Session Data & UI Model

> **SUPERSEDED** by `PLAN_msw_monitor.md` (2026-05-22).
> The `msw ui` / thin relay design described here is the correct direction;
> the implementation detail is now in PLAN_msw_monitor.md.
> `agent/` package is to be stripped after monitor is validated.

*Last updated: 2026-05-19*

---

## Design principles

1. **CLI starts sessions.** `msw run` is the entry point. Always.
2. **Data durability is in-process.** Labwatch push happens inside the task process — never depends on an external service being up.
3. **Live UI is best-effort.** If the UI server is not running, sessions are unaffected.
4. **Network never blocks session exit.** All outbound calls run in daemon threads.

---

## Labwatch push (implemented)

At `save_session_end()`, the task pushes a session summary to labwatch directly from the task process.

### Flow

```
save_session_end()
  └─ _push_to_labwatch()
       ├─ read_machine_config() → labwatch.url/username/password
       ├─ LabwatchPusher.from_machine_config() → None if not configured (skip)
       ├─ build_labwatch_payload(session_yaml, task_summary)
       └─ push_session_threaded(pusher, payload, retry_path)
            └─ daemon thread
                 ├─ success → log info
                 └─ failure → log warning + write {session_folder}/labwatch_pending.json
```

### Machine config

```yaml
# ~/.murineshiftwork/msw_machine.yaml
config_dir: /mnt/maindata/msw_configs
data_dir: /mnt/maindata/data
ui_url: http://localhost:8080        # optional, for live UI

labwatch:
  url: https://labwatch.example.org
  username: lars
  password: secret                   # or use token: abc123
```

### Idempotency

`session_basename` is the idempotency key. Pushing the same session twice (e.g. after network recovery) produces an upsert, not a duplicate. The `labwatch_pending.json` retry file in the session folder can be re-submitted manually or by a future script — importing from raw data yields the same result.

### Payload schema

```python
{
    "session_id": "AA001_20260519_120000",  # idempotency key
    "subject": "AA001",
    "task": "sequence",
    "setup": "npx2",
    "datetime": "2026-05-19T12:00:00",
    "msw_version": "2.1.1",
    "git_commit": "abc1234",
    "session_folder": "/mnt/maindata/data/AA001/sequence/...",
    "n_trials": 150,
    "task_data": {
        "total_trials": 150,
        "end_level": 9,
        "start_level": 7,
        "session_reward_count": 110,
        "session_water_ul": 330.0,
    }
}
```

### Client dependency

`labwatch_client` is served from a private registry (not PyPI — the `labwatch` name there is an unrelated homelab tool). Install separately:

```bash
pip install labwatch-client --index-url https://<private-registry>
# or from git:
pip install 'labwatch-client @ git+https://github.com/MurineShiftWork/labwatch-client.git'
```

If not installed: push silently fails to a retry file. Session is unaffected.

### Files

- `murineshiftwork/logic/labwatch.py` — `LabwatchPusher`, `build_labwatch_payload`, `push_session_threaded`
- `murineshiftwork/logic/machine_config.py` — `read_labwatch_config()`, `read_ui_url()`
- `murineshiftwork/tasks/sequence/task_objects.py` — `_push_to_labwatch()`, called from `save_session_end()`

---

## Live UI (`msw ui`) — planned

`msw ui` will start a lightweight FastAPI process that:
- Serves a static HTML page (browser-based charts — no pyqtgraph, no Qt)
- Receives trial events via `POST /ingest/{setup_name}` from `msw run`
- Fans out to `WS /events/{setup_name}` for browser subscribers
- Exposes `GET /config/subjects`, `GET /config/setups`, `GET /status`

One instance per machine covers all setups. Central lab dashboard = open
`http://<rig-hostname>:8080` in a browser from any machine on the network.

`msw run` pushes to `ui_url/ingest/{setup}` after each trial — fire-and-forget,
non-blocking. If the UI is not running, the push silently fails and the session
continues normally.

### What to strip from the current agent scaffold

The `agent/` package (Stage 1) was built with hardware ownership that is no longer
needed. Before implementing `msw ui`:

| Remove from agent/ | Keep / move |
|---|---|
| `HardwareManager` | `models.py` (adapt) |
| `POST /session/start`, `DELETE /session/active` | `GET /config/subjects`, `GET /config/setups` |
| `SessionManager.start()` / thread dispatch | `WS /events/{setup}` (add) |
| Per-setup agent URL | `POST /ingest/{setup}` (add) |

### Cross-platform startup

```bash
# Linux — tmux session or .bashrc
msw ui

# Windows — shortcut in Startup folder, or terminal
msw ui
```

No systemd, no Windows Service required. The UI is optional infrastructure.

---

## What does NOT belong in machine config

Experimenter name, project, institute, cohort, experiment — these are **session
metadata**, written into the session YAML at run time via `msw run -m` flags or
subject YAML `task_overrides`. They are not machine-level facts and should not
be in `msw_machine.yaml`.

---

## Order of remaining work

1. ~~Labwatch push adapter~~ **done**
2. Strip agent scaffold → thin event relay (`POST /ingest`, `WS /events`)
3. `msw ui` subcommand — FastAPI + static HTML frontend
4. `msw run` event push — fire-and-forget `POST /ingest` after each trial
