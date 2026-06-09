# MSW UI — Vue SPA Implementation Plan

*Created 2026-05-26. Branch target: `ft/monitor-step3`.*
*Companion doc (Python side): `PLAN_logagent_ui.md`.*
*Architecture authority: `MASTER_PLAN.md §6`.*

This document covers the Vue 3 SPA (`external/msw-ui/`) specifically:
what the scaffold already contains, what needs to change for the new LogAgent architecture,
what to borrow from the `templatevue` copier template, open questions, and the
file-by-file implementation order for `ft/monitor-step3`.

---

## 1. Source locations

| Path | What it is |
|---|---|
| `external/msw-ui/` | Vue 3 + TS + Plotly.js SPA — scaffold exists, not yet wired to backend |
| `/mnt/maindata/code/templates/templatevue/template/` | Copier template — build toolchain, runtime config injection, Docker/nginx patterns |
| `docs/work_plans/PLAN_logagent_ui.md` | Python LogAgent + API server architecture (step1 done, step2 next) |
| `docs/work_plans/MASTER_PLAN.md §6` | Locked architecture principles |

---

## 2. Architecture the Vue SPA must target

The existing scaffold was built for the **old per-setup agent** model (one FastAPI process per rig, per-setup
tab config in `agents.json`). That model is **superseded**. The locked model from `PLAN_logagent_ui.md`:

```
Setup machine (each rig)
  msw run  →  TaskProcess  →  LogAgent daemon process
                                  POST /ingest/session/{start,trial,stop}
                                  Bearer token in Authorization header

API container  (FastAPI + uvicorn, port 8080)  — one per lab machine, covers all setups
  POST /ingest/session/start    ← LogAgent
  POST /ingest/session/trial    ← LogAgent
  POST /ingest/session/stop     ← LogAgent
  GET  /sessions                → Vue UI (list; all setups)
  GET  /sessions/{uuid}         → Vue UI (metadata + plot_spec)
  GET  /sessions/{uuid}/trials?since=N   → Vue UI (incremental trial data)
  GET  /health

UI container  (nginx, port 80)  — serves pre-built Vue dist
  config.json  (volume-mounted per deployment)  →  {api_url, cameras}
```

**Key constraints (locked):**
- CLI starts all sessions. Vue UI is **read-only in v1** — no start/stop, no hardware override.
- Sessions are identified by **UUID** (`session_uuid`), not by setup name.
- Setup identity is a **field inside session data** (`"setup": "npxb"`), not a config entry.
- One API URL for the whole machine. Comes from `config.json` at runtime — no rebuild to change it.
- `agents.json` is **retired** as a multi-entry per-agent config.

---

## 3. What `templatevue` offers and what to adopt

The template at `/mnt/maindata/code/templates/templatevue/template/` provides several patterns
that the scaffold is missing. Adopt these in `ft/monitor-step3`:

### 3.1 Runtime config injection (adopt — critical)

`templatevue/template/public/config.json`:
```json
{ "api_url": "http://localhost:8080" }
```

`templatevue/template/src/config.ts` — loads `config.json` at startup via `fetch('/config.json')`,
stores it in a module-level singleton, provides `getConfig()`.

`templatevue/template/docker/40-runtime-config.sh` — nginx entrypoint.d script that copies a
volume-mounted secrets file over `/usr/share/nginx/html/config.json` before nginx starts.
Allows changing `api_url` per deployment without rebuilding the image.

`templatevue/template/docker/nginx.conf` adds a no-cache block for `config.json`:
```nginx
location ~* ^/(index\.html|config\.json)$ {
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    expires 0;
}
```

**How to adopt:** add `public/config.json`, `src/config.ts`, `docker/40-runtime-config.sh`;
update `nginx.conf` and `Dockerfile`; replace `agents.json` discovery with `config.json` loading
in `main.ts`.

### 3.2 Dockerfile improvements (adopt)

`templatevue` Dockerfile:
- `HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://localhost/ || exit 1`
- Copies `40-runtime-config.sh` and `chmod +x`

Current `msw-ui/Dockerfile` has neither. Add both.

### 3.3 Toolchain upgrades (lower priority — not blocking step3)

| | templatevue | msw-ui now |
|---|---|---|
| Package manager | pnpm | npm |
| Vite | 6 | 5 |
| TypeScript | 5.7 | 5.4 |
| vue-tsc | 2.2 | 2.0 |
| Tests | vitest + @vue/test-utils | none |
| Docs | VitePress | none |

These are nice-to-have; upgrade in a separate tidy-up pass after step3 is wired. The most valuable
of these is vitest — add at least composable-level unit tests once the polling logic is stable.

---

## 4. What the existing scaffold gets right (keep as-is or minor edits)

| File | Status | Notes |
|---|---|---|
| `src/components/PlotPanel.vue` | **Keep** | Plotly `extendTraces` + `react` on reset is correct |
| `src/components/SessionMetrics.vue` | **Minor update** | Read from UUID-keyed store instead of setup-keyed |
| `src/components/SessionHistory.vue` | **Minor update** | Read from `store.sessionsBySetup(name)` getter |
| `src/components/CameraGrid.vue` | **Minor update** | Camera list from `getConfig().cameras[setupName]` not from agent prop |
| `src/components/OverridePanel.vue` | **Defer** | Remove from SetupPanel for v1; keep file for v2 |
| `vite.config.ts` | **Keep** | `@` alias + dev proxy pattern is correct |
| `.prettierrc` / `eslint.config.js` | **Keep** | |
| `nginx.conf` | **Update** | Add no-cache rule for `config.json`; drop `agents.json` block |
| `docker-compose.yaml` | **Rewrite** | Two containers: `msw-ui` (nginx) + `msw-api` (FastAPI) |
| `Dockerfile` | **Update** | Add healthcheck + runtime-config entrypoint script |

---

## 5. What must change (architecture gap)

### 5.1 `src/types/api.ts` — full rewrite

**Remove:**
- `SessionStartRequest` — no start/stop from UI
- `HardwareStatus` — no hardware status endpoint in central server
- `AgentConfig`, `CameraConfig` — per-agent config concept retired

**Change:**
- `SessionSummary.session_id: string` → `session_uuid: string`; add `setup: string`
- `PlotPanelSpec.field: string` → `fields: { x?: string; value: string; scatter_flag?: string }`
  (matches `MASTER_PLAN §7` PlotSpec schema and `logic/plot_spec.py`)
- Add `raster` to `PlotPanelSpec.type` union
- `PlotUpdate` — keep shape; rename `PlotPanelUpdate.title` matching is still fine
- `SessionStatus` → rename/repurpose based on `GET /sessions/{uuid}` response shape (see §6)

**Add:**
```ts
export interface RuntimeConfig {
  api_url: string;
  cameras?: Record<string, CameraStreamConfig[]>;  // keyed by setup name
}

export interface CameraStreamConfig {
  name: string;
  stream_url: string;
}

export interface TrialBatch {
  session_uuid: string;
  since: number;
  last: number;
  trials: Record<string, unknown>[];
}
```

### 5.2 `src/main.ts` — rewrite

Replace `agents.json` loading with `config.json` loading. No per-agent routes at bootstrap.
Single route serves `SetupPanel`-style content; tabs are driven by `store.setupNames` reactive
getter populated after first `GET /sessions` response.

```ts
import { loadConfig } from "@/config";

async function bootstrap() {
  await loadConfig();
  // No per-agent route construction — App.vue derives tabs from store.setupNames
  const routes = [
    { path: "/:setup?", component: () => import("./components/MainView.vue") },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ];
  // ... pinia, router, mount
}
```

### 5.3 `src/App.vue` — update

Tab bar shows unique `setup` values discovered from the sessions list, plus optionally "All".
Tabs are reactive — if a new setup appears in `/sessions`, a tab appears. On first load, show a
loading state until the first poll completes.

```vue
<button
  v-for="name in store.setupNames"
  :key="name"
  :class="{ active: activeSetup === name }"
  @click="activeSetup = name"
>{{ name }}</button>
```

### 5.4 `src/composables/useAgentPolling.ts` → rename to `useMonitorPolling.ts`

Single composable for the whole app (not instantiated per setup tab).
Uses `getConfig().api_url` as the single endpoint root.

**Polling loops:**
```
GET /sessions                               every 10 s  → store.upsertSessions(list)
GET /sessions/{uuid}/trials?since=N         every 5 s   for each session where state === "running"
```

**Removed from composable:** `fetchSessionList` per agent, `startSession`, `stopSession`,
`hardwareAction`, `fetchSessionDetail` as a separate call (detail merged into session record).

**Cursor tracking:** `since=N` cursor lives in `store.liveLastTrial[session_uuid]`. On first
poll for a session, `since=0`. On subsequent polls, `since=store.getLiveLastTrial(uuid)`.

**Plot spec initialisation:** when `GET /sessions/{uuid}` response includes `plot_spec`,
call `store.initLiveSession(uuid, plot_spec)` to seed the trace accumulators.
`plot_spec` is included in the full session object returned by `GET /sessions/{uuid}`.
The `/sessions` list response may omit it for brevity — fetch `GET /sessions/{uuid}` once
when a running session first appears, then rely on trial batches.

**Reconnection:** if `/sessions` returns HTTP error or times out, set `store.offline = true`
and retry with exponential back-off (2 s, 4 s, 8 s, cap 30 s).

### 5.5 `src/stores/session.ts` — rewrite

Primary key changes from **setup name** to **session UUID**.

```ts
// Primary state
const sessions = ref<Record<string, SessionRecord>>({});         // keyed by uuid
const liveTraces = ref<Record<string, AccumulatedTrace[]>>({});  // keyed by uuid
const liveLastTrial = ref<Record<string, number>>({});           // keyed by uuid
const selectedUuid = ref<string | null>(null);                   // selected for viewing
const offline = ref(false);

// Derived
const setupNames = computed(() =>
  [...new Set(Object.values(sessions.value).map((s) => s.setup))].sort()
);
function sessionsBySetup(setup: string): SessionRecord[] {
  return Object.values(sessions.value)
    .filter((s) => s.setup === setup)
    .sort((a, b) => b.started_at.localeCompare(a.started_at));
}
function runningSessions(): SessionRecord[] {
  return Object.values(sessions.value).filter((s) => s.state === "running");
}
```

**Persistence:** keep `pick: ["liveTraces", "liveLastTrial", "selectedUuid"]`.
`sessions` is not persisted — re-fetched fresh on mount.

**Remove:** `initSetup`, `updateSessionList`, `selectSession` per setup, `updateStatus`
per setup. Replace with `upsertSession(s: SessionRecord)`, `upsertSessions(list)`.

### 5.6 `src/components/SetupPanel.vue` — update props + remove write actions

- Props: `agent: AgentConfig` → `setupName: string`
- Remove: `hardwareAction`, `startSession`, `stopSession`, `OverridePanel` usage
- Pass `setupName` to `SessionHeader`, `CameraGrid`, `PlotGrid`, `SessionMetrics`, `SessionHistory`

### 5.7 `src/components/SessionHeader.vue` — simplify (read-only)

Remove all start/stop controls. Show: state badge, setup label, subject name, task name,
elapsed time, session selector dropdown.

Session selector shows `store.sessionsBySetup(props.setupName)` and emits a UUID selection.
Selecting a session that is not running loads its historical trial data from `since=0`.

### 5.8 `src/components/PlotGrid.vue` — minor

Receive `(setupName, sessionUuid)` or just derive active UUID from store:

```ts
const uuid = computed(() =>
  props.sessionUuid ?? store.selectedUuidForSetup(props.setupName)
);
const traces = computed(() => uuid.value ? store.getLiveTraces(uuid.value) : []);
```

### 5.9 `src/components/SessionMetrics.vue` — minor

```ts
const s = computed(() => store.sessions[props.sessionUuid]);
```

---

## 6. API response shapes the Vue side expects

These must be implemented in `murineshiftwork/logagent/server.py` (step2 items).

### `GET /sessions`
```json
[
  {
    "session_uuid": "550e8400-...",
    "setup": "npxb",
    "subject": "AA001",
    "task": "sequence",
    "state": "running",
    "started_at": "2026-05-26T09:00:00+00:00",
    "ended_at": null,
    "trial_count": 42,
    "reward_count": 38,
    "liquid_ul": 114.0
  }
]
```
`reward_count` and `liquid_ul` are updated as trials arrive. `plot_spec` omitted from list for brevity.

### `GET /sessions/{uuid}`
Full `SessionRecord` including `plot_spec` (from `POST /ingest/session/start` payload):
```json
{
  "session_uuid": "...",
  "setup": "npxb",
  "subject": "AA001",
  "task": "sequence",
  "state": "running",
  "started_at": "...",
  "ended_at": null,
  "trial_count": 42,
  "reward_count": 38,
  "liquid_ul": 114.0,
  "plot_spec": {
    "version": 1,
    "task": "sequence",
    "panels": [
      {"id": "outcomes_perf", "title": "Outcomes & performance", "type": "rolling_mean",
       "fields": {"x": "trial_index", "value": "perf_buffer_mean"}, "options": {...}},
      ...
    ]
  }
}
```

### `GET /sessions/{uuid}/trials?since=N`
```json
{
  "session_uuid": "...",
  "since": 40,
  "last": 42,
  "trials": [
    {"trial_index": 40, "outcome": "correct", "perf_buffer_mean": 0.78, "liquid_ul_trial": 3.0, ...},
    {"trial_index": 41, "outcome": "incorrect", "perf_buffer_mean": 0.76, ...},
    {"trial_index": 42, "outcome": "correct", "perf_buffer_mean": 0.77, ...}
  ]
}
```
`trials` is a list of raw `trial_data` dicts as LogAgent received them. Vue applies PlotSpec
field lookups to extract `x` and `value` for each panel.

**Vue-side plot computation:** Vue does the `x/value` extraction from `trials` — it does not
receive `x_append/y_append` pre-computed. This is a change from the old agent `plot:` endpoint
design. Rationale: simpler server, richer raw data for future use.

---

## 7. Config file and deployment

### `public/config.json` (default, bundled in dist)
```json
{
  "api_url": "http://localhost:8080",
  "cameras": {}
}
```

### `docker/40-runtime-config.sh` (from templatevue)
```sh
SECRET_CONFIG_PATH="${SECRET_CONFIG_PATH:-/run/secrets/msw-ui-config.json}"
if [ -f "$SECRET_CONFIG_PATH" ]; then
    cp "$SECRET_CONFIG_PATH" /usr/share/nginx/html/config.json
fi
```

### Runtime config file per deployment (volume-mounted)
```json
{
  "api_url": "http://monitor-host:8080",
  "cameras": {
    "npxb": [
      {"name": "top",   "stream_url": "http://192.168.100.171:8001/stream.mjpg"},
      {"name": "left",  "stream_url": "http://192.168.100.172:8001/stream.mjpg"}
    ],
    "setup-1": [
      {"name": "top",   "stream_url": "http://192.168.100.111:8001/stream.mjpg"}
    ]
  }
}
```

No image rebuild needed to change `api_url` or camera URLs. Mount a new config file and restart.

### `docker-compose.monitor.yml` (two-container spec)

```yaml
services:
  msw-ui:
    build:
      context: external/msw-ui
    restart: unless-stopped
    environment:
      SECRET_CONFIG_PATH: /run/secrets/msw-ui-config.json
    volumes:
      - /mnt/maindata/msw_configs/monitor_ui_config.json:/run/secrets/msw-ui-config.json:ro
    ports:
      - "80:80"

  msw-api:
    build:
      context: .
    command: uvicorn murineshiftwork.logagent.server:app --host 0.0.0.0 --port 8080
    restart: unless-stopped
    environment:
      MSW_LOG_BEARER_TOKEN: "${MSW_LOG_BEARER_TOKEN}"
    ports:
      - "8080:8080"
```

`monitor_ui_config.json` lives in `msw_configs/` (the live config dir). The API container
bears the Python codebase — no separate published image needed in v1.

### `nginx.conf` changes
```nginx
# Add alongside the existing assets block:
location ~* ^/(index\.html|config\.json)$ {
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    expires 0;
}
# Remove agents.json-specific block (no longer served)
```

### `Dockerfile` changes
```dockerfile
# After COPY nginx.conf:
COPY docker/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh

# After EXPOSE:
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1
```

---

## 8. `msw_machine.yaml` entries for the monitor

```yaml
# ~/.murineshiftwork/msw_machine.yaml
log_url: http://localhost:8080
log_bearer_token: <token>         # LogAgent uses this to POST to API container
```

`log_url` absent → LogAgent not started, no data sent, no behavioural impact.
The Vue UI connects directly to the same `api_url` (same server, different routes).

---

## 9. Dev workflow (no Docker needed)

```bash
# Start API container locally (Python)
uvicorn murineshiftwork.logagent.server:app --reload --port 8080

# Start Vue dev server
cd external/msw-ui && npm run dev   # vite at localhost:5173
# vite.config.ts proxy /api-dev → localhost:8080 already configured
# Update proxy target if api_url differs
```

For dev against a real rig, set `api_url` in `public/config.json` to the monitor machine IP
and disable CORS in uvicorn with `--cors-allow-origin "*"` temporarily.

---

## 10. Plot computation: Vue-side vs server-side

The old agent design pre-computed `x_append/y_append` on the server (`agent/plot.py`).
The new design sends raw `trial_data` dicts and lets Vue compute the trace values from the PlotSpec.

Vue extraction for a `rolling_mean` panel with `fields: {x: "trial_index", value: "perf_buffer_mean"}`:
```ts
for (const trial of batch.trials) {
  const xVal = trial[panel.fields.x!] as number;
  const yVal = trial[panel.fields.value] as number;
  if (xVal !== undefined && yVal !== undefined) {
    trace.x.push(xVal); trace.y.push(yVal);
  }
}
```

For `histogram` panels, Vue collects all `value` field values and calls `Plotly.react` with a new
`histogram` trace (cannot use `extendTraces` for histograms — full redraw needed each poll).

For `raster` panels: `fields.x = "trial_index"`, `fields.times = "poke_times_s"` (list field).
Each trial generates one row of scatter points at y=trial_index.

This keeps the server simple and lets the Vue client be the source of truth for display logic.
The trade-off: if the UI is reloaded mid-session, it must re-fetch `since=0` to rebuild traces —
acceptable because `GET /sessions/{uuid}/trials?since=0` is a fast in-memory read on the server.

---

## 11. Session history (no localStorage needed)

Old plan had localStorage ring-buffer for history. With the central server holding sessions in
memory (ring buffer of ~20 per setup), `GET /sessions` already returns the last N sessions.
Vue can show history from the server list — no localStorage needed.

The `pinia-plugin-persistedstate` is still used to persist `liveTraces` and `liveLastTrial`
across page reloads (cursor resumption). The `sessions` list itself is not persisted.

---

## 12. `agent/` package fate

Per `MASTER_PLAN §10 ft/monitor-step4`: strip `agent/` after LogAgent + Vue UI validated on
one rig. Until then the two coexist. `msw agent start` still works but is deprecated.
The Vue SPA **does not** talk to the old agent endpoints — it only talks to the new central API.

---

## 13. Open questions

1. **Buffer size**: How many sessions / trials to keep in API container memory?
   Ring-buffer of 20 sessions per setup is the working assumption.
   If a session has 1000 trials × avg 500 bytes = 500 KB per session.
   20 sessions × 3 setups = 30 MB — acceptable for in-memory.
   Disk-backed option deferred; add if process restart loses important data in practice.

2. **`API_BASE_URL` injection at build vs. runtime**: templatevue pattern (runtime `config.json`)
   is the chosen approach. Vite `VITE_API_URL` baked-in is explicitly rejected — it requires
   a rebuild per deployment environment.

3. **Multi-rig ingest ordering**: If two rigs POST trials concurrently, the `/sessions` list is
   sorted by `started_at` desc server-side. No client-side sort needed.

4. **LogAgent crash mid-session**: If the LogAgent subprocess dies, no restart in v1.
   The gap is logged at DEBUG in the relay. Session continues unaffected; UI shows a frozen
   trial count. Acceptable for v1. Restart-on-crash deferred to v2.

5. **Histogram Plotly strategy**: `extendTraces` does not work for histograms.
   Options: (a) accumulate all raw values in the store and call `Plotly.react` on each poll;
   (b) store binned data and extend manually. Option (a) is simpler — decide when implementing
   `PlotPanel` type-aware rendering.

6. **`raster` panel rendering**: Raster requires one trace per trial (or one scatter point per
   poke per trial). Plotly `extendTraces` with multiple trace indices is possible but complex.
   Simplest: one scatter trace, accumulate `(time_s, trial_index)` pairs. Decide during step3.

7. **`plot_spec` in `/sessions` list vs. only in `GET /sessions/{uuid}`**: including full
   `plot_spec` in the list response bloats it. Fetch full record once when a session first
   appears as `"running"` (or when user selects a historical session). Cache in store.

8. **CORS**: API container must allow requests from the nginx origin. In Docker Compose,
   both containers are on the same network, so the browser sees them on different ports.
   Add `fastapi.middleware.cors.CORSMiddleware` to `logagent/server.py` with
   `allow_origins=["*"]` for LAN-only v1.

9. **`session_uuid` field name consistency**: The Python side uses `session_uuid`
   (`PLAN_logagent_ui.md`), `types/api.ts` currently uses `session_id`. Reconcile to
   `session_uuid` in both places during this sprint.

---

## 14. Implementation order

### Prerequisites (ft/monitor-step2 — must land before Vue can be wired)

- [ ] `GET /sessions/{uuid}/trials?since=N` endpoint in `logagent/server.py`
- [ ] `GET /sessions` list endpoint (check if already exists from step1)
- [ ] `GET /sessions/{uuid}` full record including `plot_spec`
- [ ] CORS middleware in `logagent/server.py`
- [ ] Verify `trial_data` field names for `sequence` and `probabilistic_switching_fixedsubjects`
  match their `plot_spec.yaml` field references

### ft/monitor-step3 — Vue SPA

Recommended order within the branch:

1. **`public/config.json` + `src/config.ts`** — foundation; unblocks everything that reads `api_url`
2. **`src/types/api.ts`** — rewrite types; breaks all components in a controlled way
3. **`src/stores/session.ts`** — rewrite store with UUID-keyed state
4. **`src/composables/useMonitorPolling.ts`** — new composable; connect to real endpoints
5. **`src/App.vue`** — tab bar from `store.setupNames`
6. **`src/main.ts`** — load `config.json`, single route
7. **`src/components/SessionHeader.vue`** — read-only header, session selector
8. **`src/components/SetupPanel.vue`** — remove write actions, update props
9. **`src/components/PlotPanel.vue`** — add type-aware rendering (rolling_mean/histogram/raster)
10. **`src/components/PlotGrid.vue`** — minor prop update
11. **`src/components/SessionMetrics.vue`** — minor store key update
12. **`src/components/SessionHistory.vue`** — minor store key update
13. **`src/components/CameraGrid.vue`** — camera list from `getConfig().cameras[setupName]`
14. **`nginx.conf`** — add no-cache for `config.json`
15. **`docker/40-runtime-config.sh`** — new file from templatevue
16. **`Dockerfile`** — add healthcheck + entrypoint script
17. **`docker-compose.monitor.yml`** — two-container compose (lives in repo root, not in external/)
18. Smoke-test: `npm run build` + serve dist + verify polling against a test LogAgent instance

### ft/monitor-step4 — strip agent/

- [ ] Remove `agent/` package
- [ ] Remove `msw agent start` CLI subcommand
- [ ] Remove `OverridePanel.vue` (or leave dormant for v2)
- [ ] Add `# TODO(msw-ui): remove after msw-ui online plotting validated` to `online_plotting.py` files

---

## 15. Files that remain unchanged from current scaffold

| File | Why unchanged |
|---|---|
| `src/components/PlotPanel.vue` | Plotly pattern is correct; only add type dispatch |
| `tsconfig*.json` | No change needed for step3 |
| `vite.config.ts` | `@` alias + dev proxy still valid |
| `eslint.config.js` / `.prettierrc` | No change |
| `src/agents.json` (bundled fallback) | Remove entirely; no longer needed |
| `config/agents.json` + `config/agents.json.example` | Replace with `config/ui_config.json.example` |

---

## 16. Relationship to other work plans

| Document | Relationship |
|---|---|
| `PLAN_logagent_ui.md` | Python side of the same sprint; defines ingest payloads and API endpoint specs |
| `MASTER_PLAN.md §6` | Locked architecture principles — never contradict these |
| `MASTER_PLAN.md §7` | PlotSpec schema — `logic/plot_spec.py` types are source of truth |
| `IMPLEMENTATION_PLAN.md` | Gap table; "msw-ui Vue SPA" row tracks overall status |
| `PLAN_camera_integration.md` | Camera config model; `CameraConfig` union affects `config.json` cameras field |
