# MSW Implementation Plan

> Generated 2026-05-18. Based on design docs in `murineshiftwork_suite/design/` and gap analysis
> against the current monolith at `src/murineshiftwork/`. The agent architecture decided in
> `DRAFT_agent_architecture.md` is treated as locked; open design questions are listed in §5.

---

## 1. Design doc summary

**`system_architecture.md`** — Defines the namespace package split. Each sub-system (`msw-agent`,
`msw-server`, `msw-tasks-*`, `msw-namespace`, `msw-readers`) is an independently installable
package contributing to the `murineshiftwork.*` implicit namespace (PEP 420: no `__init__.py`
at namespace root). The monolith tasks dir already has `__init__.py` removed (done 2026-05-14).
Not yet split into separate pip packages.

**`agent_design.md`** — The per-rig `MSWAgent` runs three child processes: `TaskProcess`,
`APIProcess` (FastAPI), `LoggerProcess`. All communicate via shared `mp.Queue`s carrying typed
dataclasses (`LogMessage`, `DataMessage`, `CommandMessage`). A prototype exists in
`backup-msw-repos/murineshiftwork/msw/agent/`. The decided architecture (see
`DRAFT_agent_architecture.md`) replaces the multiprocess design with a single FastAPI process
per rig (`murineshiftwork.agent`), wrapping the existing `TaskRunner(Thread)` model.

**`api_reference.md`** — Full HTTP surface for both the setup-agent (port 8765) and the central
server. Agent endpoints: `/hardware/*`, `/session/*`, `/config/*`, `/session/events` (WebSocket).
Server endpoints: `/registry/*`, `/rigs/{rig}/*` (proxy). None of these exist yet.

**`bpod_override_api.md`** — `BpodOverrideAPI` class in
`murineshiftwork/tasks/bpod/override.py` for firmware-level valve/LED/BNC control. Phase 1
partial equivalent (`BpodActionDriver` in `hardware/bpod/actions.py`) exists for CLI use only.
Full interactive-mode integration (inside a running session, via `handle_interactive_command`)
is unimplemented.

**`camera_acquisition.md`** — Defines `CameraClient` protocol (`start_recording`,
`stop_recording`, `is_recording`) that both `FlirBonsaiClient` and `RceConductorClient` must
satisfy. `BonsaiCameraRunner` and `MultiCameraRunner` exist in `external/msw-flir-bonsai/`.
`FlirBonsaiClient` (the `CameraClient`-compatible wrapper) is not implemented. The `SetupConfig`
`cameras` block with discriminated `RceCameraConfig`/`FlirBonsaiCameraConfig` union is not yet
discriminated — `CameraConfig` in `logic/config/models.py` is a minimal flat model.

**`task_design.md`** — `BaseTask` ABC with `start/step/stop/pause/resume/cleanup/is_completed/
handle_interactive_command/validate_params/get_parameter_schema`. Current tasks extend
`TaskRunner(Thread)` with a `run()` loop rather than `step()`. No `BaseTask` class or
`@register_task` decorator exists. Task discovery is by filesystem path convention
(`murineshiftwork.tasks.{name}.{name}.Task`), not entry points.

**`DECISIONS.md`** — Items still open: OE child session path handoff (Option A: read
`~/.cache/oe-remote/last_session` not implemented), session file schema doc not written,
readers/io split decided but not done, `TrainingScheduler` pattern agreed but not specified,
`SimulatedAnimal` mechanism verified but not implemented, interactive keymap YAML schema not
formalised, sound/XONAR sharing unresolved, timestamp precision rounding not done.

**`implementation_status.md`** — All suite packages except `one-axis-stage` and
`msw-flir-bonsai` (partial) are still templates. The priority phase ordering (namespace →
agent → tasks → server → interface → camera) is the baseline, now updated by this plan.

**`migration_and_current_package.md`** and **`package_migration_plan.md`** — Authoritative
migration path. Phase 0 (rename `murine_shift_work` → `murineshiftwork`, Qt to optional) is
done. Phase 1 (namespace foundation) is partially done: `SetupConfig`/`SubjectConfig`/
`ExecutionConfig` models and `port_by_path` are implemented. Remaining: extract into standalone
`msw-namespace` pip package, implement task entry-point registry. PyQt6/pyqtgraph remain in
install deps (tasks still import `online_plotting.py`). Meta-package extras groups not written.

---

## 2. Gap analysis table

| Area | Designed | Implemented | Gap |
|---|---|---|---|
| **Setup-agent** | `MSWAgent`, `HardwareManager`, `SessionManager`, FastAPI on port 8765, hardware lifetime across sessions | Nothing — no `agent/` dir in repo | Full build required: `agent/app.py`, `hardware_manager.py`, `session_manager.py`, `routers/` (hardware, session, config) |
| **Central server** | Thin FastAPI proxy + heartbeat registry, WS multiplexer, session history from YAML scan | Nothing — no `central/` dir | Full build required: `central/app.py`, `registry.py`, `proxy.py` |
| **Vue 3 / TS frontend** | Rig cards, session control, live trial counter via WS, HTTP Basic auth | Nothing | Full build: Vite project in `central/frontend/`, Vue components, Pinia store, WS composable |
| **CLI: agent dispatch** | `msw run` probes agent → `POST /session/start`; `msw agent {start,stop,status}` subcommand | `msw run` does direct `TaskProcess` only; no agent subcommand | Add `_find_agent()` + `_dispatch_to_agent()` to `execute.py`; add `msw agent` to `parser.py` |
| **Camera: CameraClient protocol** | `CameraClient` protocol, `FlirBonsaiClient`, `RceConductorClient`, `make_camera_client()` factory, `FlirBonsaiCameraConfig` discriminated | `BonsaiCameraRunner`/`MultiCameraRunner` exist in `external/msw-flir-bonsai/`. No `CameraClient` wrapper, no `make_camera_client`, no discriminated config union | Implement `FlirBonsaiClient` in `external/msw-flir-bonsai/msw_flir_bonsai/client.py`, `RceConductorClient` adapter, discriminated `CameraConfig` in `models.py`, factory function |
| **Camera: agent integration** | `TaskProcess._initialize_hardware()` calls `make_camera_client()`, start/stop tied to session lifecycle | No camera lifecycle integration in `TaskProcess` | Wire `make_camera_client()` call into `TaskProcess.__init__` or session hooks |
| **Barcode/TTL alignment** | `alignment.py` in readers layer; `barcode.py` mixin for tasks; `barcode_value`/`barcode_wall_time` in JSONL | `logic/barcode.py` exists, all tasks with barcodes verified; `readers/alignment.py` complete | Suite mixin class (`BarcodeMixin`) not formalised; alignment belongs in `msw-readers` (not yet extracted) |
| **Camera timestamps** | `msw_flir_bonsai.timestamps`: `unwrap_cyclic`, `preprocess_camera_csv`; FlyCapture 128s unwrap | `timestamps.py` fully implemented in `external/msw-flir-bonsai/`. `unwrap_cyclic`, `preprocess_camera_csv`, `detect_dropped_frames` done | FlyCapture-specific unwrap in `preprocess_camera_csv` is generic (calls `unwrap_cyclic` with 128s period). User has existing FlyCapture code to verify / integrate — not yet cross-checked against real hardware output |
| **Task runner isolation** | `BaseTask` ABC with `step()` loop; `TaskRunner(Thread)` wraps it; `is_completed()` drives session end | `TaskRunner(Thread)` base exists. Tasks implement `run()` loop, not `step()`. No `BaseTask`, no `is_completed()`, no `handle_interactive_command()` | Implement `BaseTask` ABC; refactor tasks to `step()` pattern (or keep `run()` and document as v1 bridge) |
| **Hardware controllers** | `BpodOverrideAPI` with `open_valve`, `close_valve`, `pulse_valve`, `reward`, `set_port_light`, `set_bnc`; full interactive integration | `BpodActionDriver` (`valve_pulse`, `valve_flush`) for Phase 1 CLI; `_write_lock` in `BpodFactory` for Phase 2 injection. No full `BpodOverrideAPI`, no LED/BNC control, no `handle_interactive_command` wiring | Implement `BpodOverrideAPI` in `hardware/bpod/override.py`; wire into task interactive mode |
| **Config system** | `SetupConfig`, `SubjectConfig`, `ExecutionConfig` with Pydantic; `port_by_path`; calibration write-back; `valve_ms_for_ul()` / `valve_s_for_ul()` | All three models implemented in `logic/config/models.py`; `port_by_path` resolves; calibration read (exponential fit) done; write-back not yet wired from calibration task | Calibration write-back from `_calibration_liquid_*` tasks not implemented; discriminated `CameraConfig` union not yet in models |
| **CLI** | `msw run`, `msw agent`, `msw setup`, `msw subject`, `msw tasks`, `msw action`, `msw calibration`, `msw post`, `msw init` | All except `msw agent` implemented | Add `msw agent {start,stop,status}` subcommand |
| **Session files** | `.msw.session.yaml` (format v2), JSONL data, `barcode_value`/`barcode_wall_time`; session file schema doc | `.msw.session.yaml` v2 implemented; JSONL implemented; session file schema doc (`session_file_schema.md`) not written | Write schema doc (DECISIONS item 5) |
| **Subject/setup config** | YAML per subject, YAML per setup, `task_overrides` sticky mode | Fully implemented including sticky task_mode writeback | Nothing to add here |
| **Reader library** | `msw-readers` standalone pkg: `alignment.py`, `validate.py`, `session.py`, `namespace.py` | All four exist in `src/murineshiftwork/readers/` in the monolith | Not yet extracted as a standalone pip package |
| **Namespace packages** | Implicit namespace packages, no `__init__.py` at `murineshiftwork/` root | `murineshiftwork/__init__.py` removed (671ac4d). `tasks/__init__.py` removed. No `__init__.py` at `murineshiftwork/tasks/` level | Top-level namespace ready; task entry-point registry not implemented; packages not split into separate repos yet |
| **Test coverage** | `SimulatedAnimal` via pybpodapi socketin; `MockBpod` injection; unit tests per package | `SimBpod` exists for hardware-free testing; `--simulate` flag works. No `SimulatedAnimal`. Hook tests (34), sequence writeback tests, reader tests exist | `SimulatedAnimal` class not implemented; agent tests not written; no integration test for agent dispatch |
| **OE integration** | `msw-open-ephys` package; Option A (read `~/.cache/oe-remote/last_session`) as immediate step | `msw_open_ephys/` in `external/`; integration with main workflow incomplete | Option A not implemented in `cli/evaluate.py` |
| **PyQt removal** | Replace `online_plotting.py` with browser polling; move Qt to optional extras | `QThread` replaced by `Thread` (54e855c). `online_plotting.py` still imported by some tasks; PyQt6 still in `install_requires` | Move PyQt6/pyqtgraph to `[extras_require] qt` in `setup.cfg`; tasks that import `online_plotting` must not in the agent path |

---

## 3. Combined implementation roadmap

### Stage 1 — Setup-agent core (2–3 weeks)

Goal: `msw agent start --setup <name>` runs a FastAPI process on port 8765 that accepts
`SessionStartRequest` and drives existing `TaskProcess`.

**New files:**
- `src/murineshiftwork/agent/app.py` — FastAPI lifespan, uvicorn entrypoint
- `src/murineshiftwork/agent/hardware_manager.py` — `HardwareManager`: holds `BpodFactory`
  across sessions; `connect(setup_config)`, `disconnect()`, `action(ActionRequest)`;
  exposes `bpod` property for injection into `TaskProcess`
- `src/murineshiftwork/agent/session_manager.py` — `SessionManager`: wraps `TaskProcess`,
  owns `TrialEvent` queue, manages state machine `idle → running → stopping → idle`
- `src/murineshiftwork/agent/routers/hardware.py` — `GET /hardware/status`,
  `POST /hardware/connect`, `POST /hardware/disconnect`, `POST /hardware/action`
- `src/murineshiftwork/agent/routers/session.py` — `GET /session/status`,
  `POST /session/start`, `POST /session/stop`, `WebSocket /session/events`
- `src/murineshiftwork/agent/routers/config.py` — `GET /config/subjects`,
  `GET /config/tasks`, `GET /config/setup`

**Modified files:**
- `src/murineshiftwork/logic/config/models.py` — add `SessionStartRequest`, `SessionStatus`,
  `TrialEvent` (already designed in `DRAFT_agent_architecture.md`)
- `src/murineshiftwork/logic/task_process.py` — ensure `bpod=` injection path is clean;
  add `TrialEvent` emission hook point after each trial (call a registered callback)
- `src/murineshiftwork/cli/parser.py` — add `msw agent {start,stop,status}` subcommand
- `src/murineshiftwork/cli/execute.py` — add `run_agent()` dispatcher

**Tests:** mock `HardwareManager` (inject `SimBpod`), test state transitions idle→running→idle
and idle→running→error; test `SessionStartRequest` serialisation round-trip.

---

### Stage 2 — CLI dispatch to agent (1 week)

Goal: `msw run` probes `localhost:8765` (or `MSW_AGENT_URL`) and dispatches via HTTP if
reachable; falls back to direct execution; `--no-agent` always bypasses.

**Modified files:**
- `src/murineshiftwork/cli/execute.py` — add `_find_agent(args_dict) -> str | None` and
  `_dispatch_to_agent(agent_url, args_dict)` (builds `SessionStartRequest` from `args_dict`,
  `POST /session/start`, polls `GET /session/status` until idle/error)
- `src/murineshiftwork/cli/parser.py` — add `--no-agent` flag to `msw run`

**Tests:** integration test with in-process FastAPI `TestClient` + `SimBpod`.

---

### Stage 3 — Central server + heartbeat registry (1–2 weeks)

Goal: `msw central start` runs a thin proxy + registry on a configurable port. Agents
register and heartbeat; web UI and CLI can address rigs by name.

**New files:**
- `src/murineshiftwork/central/app.py` — FastAPI, static file serving from `frontend/dist/`
- `src/murineshiftwork/central/registry.py` — `RigRegistry`: dict of `RigEntry(rig_name,
  agent_url, setup_name, last_seen)`, `register()`, `heartbeat()`, `get_online_rigs()` (>90s
  → offline), thread-safe with `asyncio.Lock`
- `src/murineshiftwork/central/proxy.py` — HTTP forward (`httpx.AsyncClient`) and WebSocket
  multiplexing for `/rigs/{rig}/session/events`; injects `rig_name` into `TrialEvent` stream
- Add `POST /registry/register`, `POST /registry/heartbeat`, `GET /registry/rigs`,
  `GET/POST /rigs/{rig}/session/*`, `GET /rigs/{rig}/sessions` (YAML scan)

**Modified files:**
- `src/murineshiftwork/agent/app.py` — add heartbeat task (POST to `MSW_CENTRAL_URL` every 30s)
- `src/murineshiftwork/cli/parser.py` — add `msw central {start,stop}` subcommand

**Tests:** in-memory registry expiry, proxy forwarding with mocked agent.

---

### Stage 4 — Vue 3 / TypeScript frontend (2–3 weeks)

Goal: browser UI with rig cards, session control, live trial counter. Served as static build.

**New directory:** `src/murineshiftwork/central/frontend/` (Vite + Vue 3 + TypeScript project)

**Components:**
- `App.vue` — root, HTTP Basic auth gate (stores credentials in `localStorage`)
- `RigCard.vue` — per-rig card: setup name, state badge, subject/task labels, trial/reward
  counts, elapsed time; Start button (opens `SessionStartModal`), Stop button
- `SessionStartModal.vue` — subject picker (from `GET /rigs/{rig}/config/subjects`), task
  picker, mode dropdown, Start action
- `useTrialEvents(rigName)` composable — opens WS to `/rigs/{rig}/session/events`, updates
  Pinia store on each `TrialEvent`
- `store/rigs.ts` — Pinia store: `rigs: Record<string, RigState>`, updated by WS events

**Build integration:**
- `vite.config.ts` — builds to `../dist/`
- `central/app.py` — `app.mount("/", StaticFiles(directory="central/dist"))`

**Tests:** Vitest unit tests for composable and store; no E2E in v1.

---

### Stage 5 — Camera integration (1–2 weeks)

Goal: `SetupConfig.cameras` drives camera start/stop around each session. Both `flir_bonsai`
and `rce` backends satisfy the same `CameraClient` protocol.

**New files:**
- `external/msw-flir-bonsai/msw_flir_bonsai/client.py` — `FlirBonsaiClient` implementing:
  `setup_agents()` (launch `BonsaiCameraRunner` or `MultiCameraRunner` subprocess),
  `start_recording(session_path, session_name)`, `stop_recording()`, `is_recording()`
- `src/murineshiftwork/logic/camera.py` — `CameraClient` `Protocol` definition,
  `make_camera_client(camera_cfg, data_dir) -> CameraClient | None` factory,
  `RceConductorClient` adapter

**Modified files:**
- `src/murineshiftwork/logic/config/models.py` — replace flat `CameraConfig` with
  discriminated union `RceCameraConfig | FlirBonsaiCameraConfig` (using `discriminator="backend"`)
- `src/murineshiftwork/agent/session_manager.py` — call `make_camera_client()` in session
  start; `camera_client.start_recording()` before first trial, `stop_recording()` after cleanup
- `src/murineshiftwork/logic/task_process.py` — (v1 bridge) accept `camera_client=` injection
  for direct-execution path; call start/stop in `__init__` / `__exit__`

**Timestamp integration:** `msw_flir_bonsai.timestamps.preprocess_camera_csv` is implemented.
User has existing FlyCapture 128s unwrap code — verify against real hardware CSV output before
marking complete. No code change required unless the reference output differs from
`unwrap_cyclic(values, period=128.0)`.

---

### Stage 6 — BpodOverrideAPI + interactive mode (1 week)

Goal: during a running session, interactive commands (from CLI or web UI) reach the task and
trigger firmware-level valve/LED/BNC actions.

**New files:**
- `src/murineshiftwork/hardware/bpod/override.py` — `BpodOverrideAPI`: `open_valve(port)`,
  `close_valve(port)`, `pulse_valve(port, duration_ms)`, `pulse_valve_async(...)`,
  `close_all_valves()`, `set_port_light(port, pwm)`, `set_bnc(channel, value)`,
  `reward(port, duration_ms, blocking=False)` — uses `_write_lock` from `BpodFactory`

**Modified files:**
- `src/murineshiftwork/agent/routers/session.py` — add
  `POST /session/interactive/command` endpoint dispatching to `SessionManager`
- `src/murineshiftwork/agent/session_manager.py` — forward interactive commands to task's
  `handle_interactive_command()` method (if implemented) via thread-safe call
- Tasks (`sequence`, `probabilistic_switching_fixedsubjects`, `optotagging`) — implement
  `handle_interactive_command(command, params)` using `BpodOverrideAPI`

**Keymap:** YAML `interactive_keymap:` in `task.yaml` (spec from DECISIONS item 11); parsed
in `build_task_settings()` and surfaced in `SessionStatus` for the web UI to display.

---

### Stage 7 — Readers extraction + session schema doc (1 week)

**New doc:** `docs/session_file_schema.md` (DECISIONS item 5) — JSONL format, directory layout,
required columns, `barcode_value`/`barcode_wall_time` contract, `trial_type` values.

**Package extraction:** `msw-readers` pip package containing `src/murineshiftwork/readers/`
(`alignment.py`, `validate.py`, `session.py`, `namespace.py`, `files.py`). Heavy deps (pandas,
scipy, matplotlib) declared only here, not in acquisition extras.

---

### Stage 8 — Namespace split + meta-package (2–4 weeks, parallel to other work)

Goal: individual pip packages for `msw-namespace`, `msw-logic`, `msw-tasks-sequence`,
`msw-tasks-private`, `msw-agent`, `msw-server`, `msw-readers` with extras groups on the
`murineshiftwork` meta-package (see §4).

This stage has no feature additions; it is pure packaging work. Blocked on all prior stages
being stable enough to pin versions.

---

## 4. Package split plan

| pip name | Python namespace | Status | Notes |
|---|---|---|---|
| `murineshiftwork` (meta) | `murineshiftwork` | **Monolith** — not yet split | Namespace root `__init__.py` removed; tasks `__init__.py` removed; ready for PEP 420 split |
| `msw-namespace` | `murineshiftwork.namespace` | **Implemented in monolith** | `namespace/paths.py`, `namespace/spec.py`, namespace YAML specs exist; extract as standalone when Stage 8 begins |
| `msw-logic` | `murineshiftwork.logic` + `.hardware` | **Implemented in monolith** | `SetupConfig`, `SubjectConfig`, `ExecutionConfig`, `BpodFactory`, `TaskProcess`, hooks, barcode, calibration; extract with `msw-namespace` as dep |
| `msw-agent` | `murineshiftwork.agent` | **Not started** | Stage 1 of this plan |
| `msw-server` / `msw-central` | `murineshiftwork.central` | **Not started** | Stage 3 of this plan (note: decided name is `central` not `server`) |
| `msw-interface` | Vue 3 + TS static build | **Not started** | Stage 4 of this plan |
| `msw-tasks-core` | `murineshiftwork.tasks` (registry + BaseTask) | **Not started as separate package** | `TaskRunner` base exists in monolith; `BaseTask` ABC and entry-point registry not yet written |
| `msw-tasks-sequence` | `murineshiftwork.tasks.sequence` | **In monolith** — `tasks/sequence/` | Must not import PyQt; no `online_plotting` import in agent path |
| `msw-tasks-private` | `murineshiftwork.tasks.*` (all others) | **In monolith** | All tasks exist in monolith; `optotagging` consolidated 2026-05-18 |
| `msw-readers` | `murineshiftwork.readers` | **In monolith** | `readers/alignment.py`, `validate.py`, `session.py`, `namespace.py` all exist; extract as Stage 7 |
| `msw-open-ephys` | `murineshiftwork.open_ephys` | **Scaffolded in `external/`** | OE HTTP remote; integration with CLI not complete |
| `msw-flir-bonsai` | `msw_flir_bonsai` | **Partial** — runner + timestamps done | `FlirBonsaiClient` (CameraClient wrapper) not yet written; Stage 5 |
| `one-axis-stage` | `one_axis_stage` | **Mature** | No changes needed |
| `ttl_barcoder` | `ttl_barcoder` | **Mature** | No changes needed |
| `pypulsepal` | `pypulsepal` | **In use** | Already replaces `stimulation.py` for optotagging |

**Migration path:**
1. Stages 1–7 build everything into the monolith at `src/murineshiftwork/agent/` and
   `src/murineshiftwork/central/`.
2. Stage 8: add `pyproject.toml` extras groups; `find_namespace_packages(where="src")` already
   works once `__init__.py` is absent at namespace roots.
3. Task namespace split: remove any remaining `__init__.py` at `murineshiftwork/tasks/`; add
   entry-point declarations to each task package's `pyproject.toml`.
4. Clean break criteria (from `migration_and_current_package.md`): agent stable on hardware,
   `sequence` + `probabilistic_switching_fixedsubjects` + `optotagging` ported to `BaseTask`
   `step()` interface, JSONL parity confirmed by existing reader tests.

---

## 5. Open design questions

1. **`step()` vs `run()` migration path.** The current `TaskRunner.run()` loop is blocking
   per-trial via pybpodapi's `run_state_machine()`. The `step()` design assumes `TaskProcess`
   calls `task.step()` in a ~1 ms loop. For Bpod tasks, one `step()` call = one blocking trial
   run, so the loop frequency is irrelevant — but the interface change requires touching every
   task. Decision needed: adopt `BaseTask.step()` now for all tasks, or keep `run()` in v1 as
   a bridge and only require `step()` for new suite tasks?

2. **`TaskProcess` in agent: Thread vs multiprocess.** The suite design (`agent_design.md`) uses
   `mp.Process` for isolation. `DRAFT_agent_architecture.md` (decided) uses `Thread` inside a
   FastAPI process. This is fine for task crashes (caught in `try/except BaseException`) but a
   hung `run_state_machine()` call in a Thread will block the FastAPI event loop if they share
   the thread pool. Confirm: `TaskRunner` runs in a daemon Thread; FastAPI runs in uvicorn's
   main asyncio loop — no sharing, no blocking. Needs explicit verification with uvicorn's
   `--workers 1` and a blocking task.

3. **Discriminated `CameraConfig` union.** Current `CameraConfig` in `models.py` is a flat model
   with `backend: str`. The design requires a discriminated union
   `RceCameraConfig | FlirBonsaiCameraConfig`. Changing this is a breaking change to existing
   setup YAMLs on rigs that have `cameras:` blocks. Migration strategy needed (warn + auto-upgrade
   on load, or manual YAML edit).

4. **`online_plotting.py` removal timeline.** Three tasks (`sequence`, `probabilistic_switching`,
   `probabilistic_switching_fixedsubjects`) import `online_plotting.py` which imports `pyqtgraph`.
   Removing Qt from `install_requires` requires ensuring these imports are never hit in the agent
   path. Current approach: import is inside `run_task()` body, not at module level — but this
   needs verification per task. PyQt6 stays in deps until Stage 4 (Vue frontend) is done.

5. **OE child session (DECISIONS item 2, Option A).** Reading `~/.cache/oe-remote/last_session`
   at `msw run` time is a 20-line change to `cli/evaluate.py`. This is the highest-value
   workflow improvement not yet done. No blocking dependency — can be implemented independently
   of all stages above.

6. **Calibration write-back.** `SetupConfig.valve_ms_for_ul()` is implemented (exponential fit).
   The write path — `_calibration_liquid_dynamic` and `_calibration_liquid_static` tasks writing
   measured points back to the setup YAML — is not wired. Both tasks need a post-run call to a
   `save_valve_calibration(config_dir, setup_name, port, points)` helper that does a
   read-modify-write on the YAML. This is blocked on nothing; implement alongside Stage 1 or
   as a standalone fix.

7. **`SimulatedAnimal` priority.** The mechanism is verified (pybpodapi `socketin` on
   `PYBPOD_API_PORT`). Implementing `SimulatedAnimal` in
   `src/murineshiftwork/hardware/bpod/sim.py` (next to `SimBpod`) would enable full end-to-end
   task tests without hardware. This is a high-value testing investment; suggest doing it in
   parallel with Stage 1 so agent tests can use it.

8. **Auth on setup-agent.** `DRAFT_agent_architecture.md` specifies HTTP Basic with
   `MSW_AGENT_PASSWORD` env var. This is Stage 5 (auth + hardening). In v1 development, the
   agent runs without auth on the LAN. Ensure the FastAPI app structure makes adding Basic auth
   middleware non-breaking (add as a dependency on all routers, not baked into route logic).

9. **Timestamp precision (DECISIONS item C).** Rounding JSONL float timestamps to 4 decimal
   places is a safe change (Bpod resolution is ~1 ms). Confirm no test fixture uses full-precision
   timestamps as dict keys, then implement in `logic/io.py` `_NumpyEncoder`. Low risk, do with
   any nearby commit.

10. **Windows agent scope.** `DRAFT_agent_architecture.md` explicitly defers Windows agent to
    v2. The current `msw-tasks-sequence` / Win11 deployment uses direct `TaskProcess` execution.
    Confirm this path remains supported under `msw run --no-agent` indefinitely, not deprecated.
