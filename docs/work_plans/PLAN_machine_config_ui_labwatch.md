# Machine Config, UI Broadcast & Labwatch Integration Plan

*Status: partially implemented. Last updated: 2026-05-20*

---

## What is implemented

- `labwatch:` block in `msw_machine.yaml` (schema defined, read by `read_labwatch_config()`)
- `ui_url:` key in `msw_machine.yaml` (read by `read_ui_url()`)
- `LabwatchPusher` adapter stub in `murineshiftwork/logic/labwatch.py`
- `build_labwatch_payload()` — maps MSW session YAML + task summary → labwatch schema
- `push_session_threaded()` — daemon thread, writes `labwatch_pending.json` on failure
- `_push_to_labwatch()` in `TaskControl.save_session_end()` (sequence task)

---

## Machine config schema (current + planned)

```yaml
# ~/.murineshiftwork/msw_machine.yaml

config_dir: /mnt/maindata/msw_configs   # shared config repo
data_dir: /mnt/maindata/data             # default session output root

ui_url: http://localhost:8080            # optional; msw ui listens here

labwatch:
  url: https://labwatch.example.org
  username: lars
  password: secret                       # or: token: abc123
```

### Open question: output dir ownership

`data_dir` in machine config is the default root for session output. The CLI
`--out-path` flag and `MSW_DATA_DIR` env var override it (existing priority chain
in `resolve_data_dir()`). This is already implemented and working.

**No further config needed for output dir** — the current priority chain covers
all cases (machine-local default → env override → CLI override).

### What does NOT belong in machine config

Experimenter name, project, institute, cohort, experiment — these are session
metadata, set via `msw run -m key=value` or subject YAML `task_overrides`. They
are not machine-level facts.

---

## Labwatch: open questions

1. **Client package name and registry URL** — `labwatch_client` from a private
   registry. Not yet available. The `LabwatchPusher.push()` stub is ready; fill
   in the import and `Client(url, username, password).sessions.upsert(payload)`
   call once the client ships.

2. **Payload schema** — current `build_labwatch_payload()` sends:
   - `session_id` (idempotency key = `session_basename`)
   - subject, task, setup, datetime, msw_version, git_commit, session_folder
   - `n_trials`, `task_data` dict (task-specific summary)

   **Needs verification** against actual labwatch schema once client is available.
   The `task_data` block is intentionally flexible — map to labwatch fields there.

3. **Token vs password** — current code reads `labwatch.token` as fallback for
   `labwatch.password`. Confirm which the client expects.

4. **Retry strategy** — on network failure: `labwatch_pending.json` written to
   session folder. Re-import from raw data yields the same payload (idempotent).
   No retry CLI planned — manual re-run or import pipeline covers this.

5. **Per-task vs global push** — currently only the `sequence` task calls
   `_push_to_labwatch()`. Other tasks (fixedsubjects, optotagging, etc.) need
   the same pattern added to their `save_session_end()` equivalents once the
   schema is confirmed. Consider moving to a base class method in `TaskProcess`
   so it's automatic for all tasks.

---

## UI broadcast (`msw ui`): planned, not started

### Design

- `msw ui` starts a FastAPI process (thin, no Qt/pyqtgraph)
- Serves static HTML page — browser-based live charts (Chart.js or uPlot)
- One instance per machine covers all setups
- `msw run` pushes trial events to `{ui_url}/ingest/{setup_name}` after each
  trial (fire-and-forget, non-blocking daemon thread)
- UI fans events to `WS /events/{setup_name}` for browser subscribers
- `GET /config/subjects`, `GET /config/setups`, `GET /status` for UI dropdowns

### What to do with the current `agent/` scaffold

The `agent/` package was built with hardware ownership (HardwareManager,
SessionManager with `POST /session/start`) that the revised design does not need.

**Strip from `agent/` before renaming to `ui/`:**
- `HardwareManager` — remove entirely
- `POST /session/start`, `DELETE /session/active` — remove
- `SessionManager.start()` / thread dispatch — remove; replace with passive state

**Keep / adapt:**
- `models.py` — adapt for event relay
- `GET /config/subjects`, `GET /config/setups` — keep
- `WS /events/{setup}` — rename from `/session/events`, make setup-scoped
- Add `POST /ingest/{setup_name}` — receives trial events from `msw run`
- Add `GET /status` — shows all known setups and last-seen event per setup

### Cross-platform startup

```bash
# Linux — tmux / .bashrc
msw ui

# Windows — shortcut in Startup folder, or terminal on login
msw ui
```

No systemd, no Windows Service needed. UI process is optional infrastructure;
if it's not running, `msw run` continues normally (push silently fails).

### Open questions

1. **Frontend library** — Chart.js (simpler, CDN) vs uPlot (faster for dense
   time-series, no CDN needed). Decision: uPlot preferred for trial-dense sessions
   (>500 trials). TBD.

2. **Static HTML location** — bundle as package data in `murineshiftwork/ui/static/`
   or generate at startup? Package data preferred for offline rig use.

3. **`msw run` event push** — push after each trial using `threading.Thread` +
   `httpx` (sync client in thread). Use `httpx` not `requests` for consistency
   with labwatch client. Timeout: 0.5 s. If timeout hit → skip silently, no retry.

4. **Auth** — `MSW_UI_PASSWORD` env var → HTTP Basic, same pattern as agent.
   Default: open (rig is on private network).

---

## Implementation order

| Step | Status | Notes |
|---|---|---|
| `data_dir` in machine config | done | existing `resolve_data_dir()` |
| `ui_url` key in machine config | done | `read_ui_url()` added |
| `labwatch:` block in machine config | done | `read_labwatch_config()` added |
| `LabwatchPusher` stub | done | waiting for client package |
| `push_session_threaded` | done | tested, writes retry file on failure |
| `_push_to_labwatch` in sequence task | done | called from `save_session_end()` |
| Extend to other tasks | todo | base class method preferred |
| Strip `agent/` → thin relay | todo | remove hardware ownership layer |
| `POST /ingest/{setup}` + `WS /events` | todo | core of `msw ui` |
| Static HTML frontend | todo | uPlot charts, WS subscribe |
| `msw run` fire-and-forget push | todo | httpx in daemon thread |
| `msw ui` CLI subcommand | todo | add to parser, execute |
