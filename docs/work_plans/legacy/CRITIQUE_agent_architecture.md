# Architecture Critique: MSW Agent Design

> Second opinion on `DRAFT_agent_architecture.md` and `IMPLEMENTATION_PLAN.md`.
> Written 2026-05-19. This is not a decision document — it is a review to inform the
> architecture discussion. Points are stated directly and with a recommendation per item.

---

## 1. Central server necessity

The hub-and-spoke model is justified by the stated constraint: rigs cannot reach each other
but all can reach one lab server. Given that constraint the design is correct in principle.
The question is whether the implementation earns its keep.

The risk is a single point of failure that cannot fail gracefully. If the central server
process crashes, the web UI and any cross-rig CLI operations stop working — but crucially,
**running sessions on rigs are unaffected** because `TaskProcess` is inside the agent, not
the central server. That is a good property and should be preserved explicitly in the design.
What is not addressed is what happens when the central server is unreachable at session-start
time: the CLI falls back to direct execution, but a user relying on the web UI is simply
blocked. There is no documented degraded-mode procedure.

The alternatives worth considering: Tailscale (or equivalent WireGuard mesh) eliminates the
need for a central proxy by making every rig directly addressable from any machine on the lab
network without going through a dedicated server process. Installation is one command per
machine and requires no code at all on the MSW side. mDNS/Avahi gives discovery on the local
subnet only, which does not solve the isolated-network problem. MQTT/Redis pub-sub shifts
complexity to an external broker and is over-engineered for four rigs.

**Recommendation:** keep the central server but make its failure mode explicit in the design.
Document that the central server is a convenience layer only — rigs must be fully operable via
direct `msw run` or `msw run --no-agent` without it. Add a health-check note that if Tailscale
or a site-wide VPN is ever deployed, the central proxy layer becomes optional and can be
removed. Do not over-engineer for that eventuality now, but do not make the central server
load-bearing for rig operation.

---

## 2. Agent-pull vs agent-push

The current design is client-push: the web UI (via the central proxy) pushes start/stop
commands to agents. Agents push heartbeats to the central server. The WebSocket for trial
events flows agent → central → browser. This is coherent and correct for the use case.

The alternative — agents long-polling a job queue on the central server — would mean agents
actively check for new work. This shifts the TCP connection direction, which can help when
agents are behind NAT that does not allow inbound connections. The architecture document does
not state whether agents can receive inbound TCP connections from the central server. If the
lab network topology means the central server cannot initiate HTTP connections to port 8765 on
the rig machines (one-way routing), then the current proxy design is broken as written: the
central server's `proxy.py` must be able to open a connection to `agent_url`. If routing is
one-way in the other direction (agents can reach central, central cannot reach agents), a
job-queue / long-poll design is necessary.

**Recommendation:** explicitly confirm the network topology before writing `proxy.py`. If the
central server can open TCP connections to agent port 8765 (i.e., routing is symmetric between
server and rig machines), the push model is fine and simpler. If routing is asymmetric
(agents → central only), switch to agents maintaining a persistent outbound WebSocket to the
central server and receiving commands over it. This is a foundational decision that cannot be
patched later without rewriting the proxy.

---

## 3. Heartbeat + in-memory registry

The in-memory registry is the right default for a first cut — it is simple, has no
dependencies, and the failure mode on central server restart is benign (agents re-register
within 30 seconds on next heartbeat). This is acceptable at the current scale.

The concern is not persistence of rig state; it is persistence of the heartbeat schedule. If
the central server restarts and all four rigs are mid-session, the registry is empty for up to
30 seconds. During that window the web UI shows all rigs offline while sessions are still
running. The design should document this as an expected transient, not a bug, and the UI
should handle the "all rigs offline immediately after server start" state gracefully rather
than showing an alarm.

A larger concern: `asyncio.Lock` for registry access is correct for a single-process uvicorn
deployment, but if anyone runs `uvicorn --workers N` (multi-process), the lock is per-process
and the registry diverges instantly. The design says nothing about this. With `--workers 1`
(which uvicorn defaults to for development) this is fine. It should be enforced.

**Recommendation:** keep in-memory registry. Explicitly document `--workers 1` as the only
supported uvicorn configuration for the central server. Add a comment in `registry.py` that
multi-worker deployment requires an external store (Redis). No need to implement Redis now.
Have the UI show "reconnecting..." for the first 30 seconds after server start rather than
alarming on offline rigs.

---

## 4. Session database: "no database, scan YAML files"

The plan's "no database" decision is reasonable for the current scale, but it creates an
invisible performance cliff. At 4 rigs × 100 sessions/day, the data directory accumulates
~400 `.msw.session.yaml` files per day. `GET /rigs/{rig}/sessions` scans all of them. Within
a week you have 2,800+ files. Within a month, ~12,000. A linear file-system scan of 12,000
YAML files to render a session history page will be noticeably slow and will surprise whoever
hits it first.

A minimal SQLite session index is not a "database" in the heavyweight sense — it is a
300-line file, requires no server, and adds zero operational burden. The index can be written
by `TaskProcess` at session end (one INSERT) and read by the central server for history
queries. It does not replace YAML files as the source of truth. The readers library can still
read YAML directly for analysis; the index is only for the UI history endpoint.

**Recommendation:** implement a minimal SQLite index (`~/.murineshiftwork/sessions.db`,
schema: `session_id, rig_name, subject, task, started_at, ended_at, trial_count, session_folder`)
written at session close. If it does not exist, fall back to the YAML scan. This is a
one-morning task with no architectural impact and it prevents the scan from becoming a problem
at 6 months of data.

---

## 5. FastAPI per rig vs simpler approaches

FastAPI is not a bad choice here, but the design should be honest about what it costs. FastAPI
brings Pydantic validation, async support, automatic OpenAPI docs, and straightforward
WebSocket handling. For a rig daemon that handles one session at a time and a handful of
config reads, this is substantial framework weight for modest benefit. The same API could be
implemented in 200 lines of `http.server` or Flask with no async. The async event loop is
specifically a liability when wrapping a blocking `TaskRunner(Thread)` — see section 6.

The counterargument is that the design already depends on Pydantic for config models, and the
central server is also FastAPI, so the operational familiarity is consistent. A ZMQ REQ/REP
socket (one natural fit for a command/response hardware daemon) would be lighter but would
require the Vue frontend to speak a different protocol for live events, adding complexity
elsewhere.

**Recommendation:** keep FastAPI for the agent, but only because the project already depends
on Pydantic and the team is presumably familiar with it. Do not add async route handlers for
session start/stop — use `run_in_executor` or a synchronous endpoint with
`SessionManager` managing state transitions in the background thread. Write a clear comment
in `session_manager.py` explaining that session operations are asynchronous from the HTTP
caller's perspective: `POST /session/start` returns immediately with `{session_id}` and the
caller polls `GET /session/status`. This is already implied by the design but not stated.

---

## 6. Hardware lifetime model under uvicorn

Holding the Bpod serial handle open across sessions inside a uvicorn process is the right
call — reconnecting serial hardware per session is slow and fragile. The risk is in how the
`HardwareManager` handle interacts with uvicorn's process lifecycle.

Uvicorn runs the FastAPI lifespan (startup/shutdown) in the asyncio event loop. The serial
port is a blocking I/O resource. If the Bpod serial driver (pybpodapi) does any blocking
reads in its keepalive or error detection path, and if those end up called from async context,
the event loop stalls. The design avoids this if `HardwareManager` is only touched from the
`TaskRunner` thread (synchronous path) and from HTTP route handlers (which must call
`HardwareManager` via `loop.run_in_executor`). This is not stated in the design, and it is
easy for a future contributor to add a direct synchronous call from an async route handler.

A second risk: uvicorn catches `SIGTERM` and calls the FastAPI shutdown lifespan. If a task
is mid-trial when the process receives `SIGTERM` (e.g., `systemd stop msw-agent`), the
shutdown lifespan has a deadline. If `TaskRunner` is blocking on `run_state_machine()` and
does not respond to the stop signal within that deadline, uvicorn kills the process hard,
leaving Bpod in an unknown state.

**Recommendation:** document in `app.py` lifespan that `HardwareManager` methods must always
be called from the `TaskRunner` thread or via `asyncio.to_thread` from async routes — never
with direct synchronous calls from async handlers. Add a bounded `stop()` with a 5-second
timeout in the lifespan shutdown hook so that a hung trial gets a hard stop rather than an
indefinite hang. Add a `TaskRunner.request_stop()` method that sets a threading.Event checked
at trial boundaries so `SIGTERM` can be handled gracefully.

---

## 7. TaskProcess isolation: Thread vs Process

The design explicitly chose `Thread` over `multiprocessing.Process` for simplicity. The
blast-radius difference is significant and worth stating plainly: a task crash that raises an
unhandled exception inside a `Thread` is caught by the `try/except BaseException` in
`TaskRunner.run()` — the agent process survives and the state machine transitions to `error`.
This is fine for normal exceptions. A task that calls into a C extension (pybpodapi wraps
serial I/O) and triggers a segfault, or a task that calls `os._exit()`, or a task that
exhausts memory, will kill the entire agent process including the FastAPI server. With a
`Process`, only the task process dies; the agent can detect this via `Process.exitcode` and
transition to `error` cleanly.

The cost of `multiprocessing.Process` is real: you cannot inject a live Bpod handle across a
process boundary because it holds a serial port file descriptor. You would need to restructure
so the Bpod handle lives in the task process, not the agent, which removes the
"hardware stays connected across sessions" property. The suite design's original three-process
model solved this with a `HardwareProcess` that owned the handle and communicated via Queue
— which is why it used that architecture.

**Recommendation:** keep `Thread` for v1 because the Bpod injection dependency makes Process
isolation non-trivial. Accept the crash blast-radius limitation explicitly in the design doc,
not just in the implementation plan's open question. Mitigate it by running the agent under
`systemd` with `Restart=on-failure` so a crash brings it back within seconds. Write that
systemd unit file as part of Stage 5 hardening, not as an afterthought.

---

## 8. Vue 3 + Vite complexity vs HTMX/Jinja2

The Vue 3 + Vite choice introduces a build pipeline that requires Node.js on the developer
machine, a separate build step before any UI change is visible, TypeScript compilation, and
ongoing npm dependency management. For a lab tool used by five people to start sessions on
twenty rigs, this is a significant ongoing maintenance burden. The Vue/TS dependency tree will
accumulate CVEs and breaking changes faster than any other part of the stack.

What Vue specifically adds over HTMX: reactive per-rig trial counters updated via WebSocket
without full-page reloads, a component model that makes RigCard reusable across rigs, and
TypeScript type safety on the `TrialEvent` schema. HTMX with server-sent events (SSE) or
WebSocket swap extensions can handle the live trial counter case with no build step and no
JavaScript component framework. The rig-card grid could be a Jinja2 template with an SSE
listener per card updating a `<span id="trial-count-{rig}">` inline.

The honest case for Vue is that if the v2 deferred features (performance plots, session
replay, protocol builder) are ever built, HTMX becomes genuinely awkward and Vue pays off.
If v2 is unlikely to happen, Vue is pre-optimising for features that will not be built.

**Recommendation:** if you have confidence v2 features will be built in 12 months, keep Vue.
If v2 is aspirational, use HTMX + Jinja2 + SSE for v1. The HTMX approach would take 2–3
days to implement vs 2–3 weeks for Vue, and could be replaced with Vue later if v2 scope
justifies it. The Vue decision should be made with eyes open about what you are buying in
terms of build pipeline maintenance over the 3-year lifespan of this tool.

---

## 9. Auth model

HTTP Basic over plain HTTP sends credentials as base64 in every request. Base64 is not
encryption. Anyone on the lab network who can see TCP traffic (a switched network does not
mean eavesdropping is impossible — ARP poisoning, a misconfigured hub, or a compromised
machine on the same subnet) can extract the `MSW_AGENT_PASSWORD` from a single captured
request. Once extracted, they can send `POST /session/stop` to any rig or `POST
/hardware/action` to open valves.

For an isolated lab network with physical access controls and no internet-facing exposure,
this risk may be acceptable. It is not acceptable if the lab network is connected to a
university network or has WiFi access points, which most modern labs do.

The design defers TLS to "add nginx TLS terminator if exposed beyond lab LAN." This framing
underestimates how often "lab LAN" and "university network" are not physically separate. A
self-signed cert with nginx in front of both the central server and each agent is a
half-day setup, not a v2 project. `mkcert` can generate a trusted local CA in minutes.

**Recommendation:** use HTTP Basic for v1 development on an isolated test network only. Add a
clear warning in the startup log if `MSW_AGENT_PASSWORD` is set but TLS is not configured.
Plan nginx TLS termination as part of Stage 5 hardening, not as a "if exposed beyond LAN"
contingency. The question is not whether you will add TLS — it is whether you do it before or
after the first password is captured.

---

## 10. Stage 8: namespace split sequencing

The plan defers the namespace split until all other stages are stable. The stated rationale is
that splitting into separate pip packages before the APIs are stable creates churning version
pins. That reasoning is sound. The risk of deferral is different: building Stages 1–7 inside
the monolith means the agent and central server code will accumulate imports of monolith
internals that would be import-cycle violations in the split world. It is easy to write
`from murineshiftwork.logic.task_process import TaskProcess` inside `agent/session_manager.py`
— perfectly legal in the monolith, but it means `msw-agent` will depend on `msw-logic` rather
than on a stable `msw-tasks-core` interface. By Stage 8, untangling those imports is a
significant effort.

The alternative is not to split packages early — it is to enforce the split's import
boundaries now, as a linting rule, even while everything lives in one repo. Define which
namespaces are allowed to import which other namespaces and add a CI check (e.g., `import-linter`
or a simple grep-based gate). This costs one day and prevents boundary violations from
accumulating across seven stages of development.

**Recommendation:** do not split packages early. Do add an import boundary policy document
and a CI lint rule that enforces it before Stage 1 begins. The specific rule needed is: code
under `murineshiftwork.agent.*` may import `murineshiftwork.logic.*` and
`murineshiftwork.hardware.*` but not `murineshiftwork.tasks.*` directly (tasks are loaded
by name at runtime). Catching a boundary violation in CI on day one of Stage 1 is
incomparably cheaper than refactoring it in Stage 8.
