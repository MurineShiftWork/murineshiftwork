# MSW Package Graph

*Created 2026-05-30. Captures expected final package graph and open naming/scope decisions.*
*Supersedes §4 of `IMPLEMENTATION_PLAN.md` for package graph design; gap-table status tracking stays there.*

---

## Expected package graph

```
murineshiftwork                      ← metapackage; install this
  core deps (always):
    acquisition-namespace ≥ 1.0      ← hardware abstraction namespace (standalone)
    ttl-barcoder                     ← TTL barcode pipeline (standalone)
    msw-core          [TBD name]     ← config, task_process, hardware, barcode logic (from monolith)

  extras:
    [tasks]       → msw-tasks        ← task definitions (sequence, switching, calibration, …)
    [readers]     → msw-readers      ← session readers + alignment
    [agent]       → msw-agent        ← FastAPI rig agent
    [flir]        → msw-flir-bonsai  ← FLIR camera via Bonsai (Windows only)
    [rce]         → rpi-camera-ensemble
    [calibration] → serial-scale-hx711, serial-scale-bench
    [labwatch]    → msw-labwatch     ← thin wrapper over private labwatch_client
    [dev]         → pytest, ruff, mypy, ... (unchanged)
    [docs]        → mkdocs-material (unchanged)

Standalone packages (MurineShiftWork org, not MSW namespace):
  acquisition-namespace
  pypulsepal
  ttl-barcoder
  rpi-camera-ensemble
  msw-flir-bonsai
  one-axis-stage
  serial-scale-bench
  serial-scale-hx711
  rfid-to-url
  msw-oe              ← OE plugin (entry-point group; separate repo, not yet created)
```

---

## Per-package status

| Package | Location | Status |
|---|---|---|
| `murineshiftwork` | `src/murineshiftwork/` | Monolith; `__init__.py` removed at namespace root — PEP 420 ready |
| `acquisition-namespace` | `external/` + PyPI dep `≥1.0` | External; publication status: verify on PyPI before next release |
| `ttl-barcoder` | external + PyPI | Standalone, published; pin in pyproject.toml is `==0.3.0` |
| `msw-core` [TBD] | in monolith: `logic/`, `hardware/`, `namespace/` | Not extracted; blocked on decisions below |
| `msw-tasks` [TBD] | in monolith: `tasks/` | Not extracted; task-group granularity open (see below) |
| `msw-readers` | in monolith: `readers/` | Not extracted; Phase 3 reader work in progress |
| `msw-agent` | in monolith: `agent/` | Stage 1 done; Stage 2 next; strip deprecated `agent/` after monitor validated |
| `msw-flir-bonsai` | `external/msw-flir-bonsai/` | BonsaiCameraRunner + FlirBonsaiClient done; minor CI gaps (see PLAN_external_packages.md) |
| `msw-oe` | not yet | Plugin contract live in MSW; separate repo not created |
| `rpi-camera-ensemble` | `external/provision_rpi/rpi_camera_ensemble/` | Toolchain done 2026-05-26; 3 commits pending; not yet on GitHub/PyPI |
| `pypulsepal` | `external/pypulsepal/` | Published; under `larsrollik/` — transfer to org pending |
| `one-axis-stage` | `external/one-axis-stage/` | Mature; under `larsrollik/` — transfer to org pending |
| `serial-scale-bench` | `external/serial_scale_bench/` | Minor CI gaps; VERSION missing |
| `serial-scale-hx711` | `external/serial_scale_hx711/` | Same gaps as serial-scale-bench |
| `rfid-to-url` | `external/rfid-to-url/` | Full legacy migration needed (setuptools → hatchling) |

---

## Open decisions (needed before extraction sprint)

### 1. `msw-namespace` fate
IMPLEMENTATION_PLAN.md §4 plans `msw-namespace` as a standalone pip package containing `NamespaceBuilder` + `namespace.msw.yaml`.
PLAN_namespace_unification.md Sprint 3 describes the extraction.

**Question:** Is `msw-namespace` still extracted as a separate package, or is `NamespaceBuilder` absorbed into:
- (a) `acquisition-namespace` — makes it the shared namespace layer for all acq tools, or
- (b) `msw-core` — keeps it internal to the MSW stack

> **→ Decision needed.** Current code: `NamespaceBuilder` lives in `src/murineshiftwork/namespace/`.

---

### 2. `msw-logic` → `msw-core` rename
IMPLEMENTATION_PLAN.md §4 names the core logic package `msw-logic`.
Working name in this discussion: `msw-core`.

**Question:** Confirm rename to `msw-core`, and clarify scope:
- Does `msw-core` include only `logic/` + `hardware/`, or also `namespace/` (i.e. it absorbs decision 1b)?
- Python namespace: `murineshiftwork.logic` + `murineshiftwork.hardware`, or a new root?

> **→ Decision needed.**

---

### 3. Task package granularity
IMPLEMENTATION_PLAN.md §4 locks `msw-tasks-{core,sequence,switching,other}` (4 packages, prefix `msw-tasks-`).
Working name in this discussion: `msw-tasks` (singular).

**Options:**
- (a) Single `msw-tasks` package containing all tasks — simpler; `[tasks]` extra on metapackage is just this one package
- (b) Keep four `msw-tasks-*` packages; `[tasks]` on metapackage pulls all four; `[tasks-sequence]` etc. for fine-grained installs
- (c) Keep four packages but expose only `[tasks]` (pulls all) on the metapackage; internal granularity hidden from users

> **→ Decision needed.** Extraction order (core → sequence → switching → other) is unchanged regardless of naming.

---

### 4. `msw-agent` install scope
Current plan: `[agent]` extra on the metapackage.

**Question:** Should `msw-agent` (FastAPI rig agent) be a core dep (always installed) or remain an opt-in extra?
- Core dep means every `pip install murineshiftwork` pulls in FastAPI + uvicorn
- Extra keeps base install lightweight for analysis/reader-only use cases

> **→ Decision needed.**

---

## Extras restructure (planned, branch `ft/extras-restructure`)

Current extras vs. planned:

| Current extra | Proposed | Notes |
|---|---|---|
| `[dev]` | `[dev]` | Unchanged |
| `[docs]` | `[docs]` | Unchanged |
| `[agent]` | `[agent]` | FastAPI + uvicorn + websockets |
| `[calibration]` | `[calibration]` | serial-scale-hx711, serial-scale-bench |
| `[rce]` | `[rce]` | rpi-camera-ensemble |
| `[qt]` | `[qt]` | PyQt6 + pyqtgraph — until msw-ui validated, then remove |
| `[keyboard]` | into `[acquisition]` or `[tasks]` | sshkeyboard; not a standalone extra |
| — | `[tasks]` | msw-tasks (new; depends on decision 3) |
| — | `[readers]` | msw-readers (new) |
| — | `[flir]` | msw-flir-bonsai (new) |
| `[labwatch]` | `[labwatch]` | msw-labwatch once released |

---

## Extraction order (unchanged)

1. `msw-tasks-core` (minimal deps — good first split test)
2. `msw-tasks-sequence` (self-contained; agent path must stay PyQt-free)
3. `msw-core` / `msw-logic` + namespace layer (base; unblocks all others)
4. `msw-agent` (already structurally isolated)
5. `msw-readers` (no hardware deps)
6. `msw-tasks-switching` (depends on camera client stable)
7. `msw-tasks-other` (internal-use, no urgency)

Blocked on: decisions 1–4 above, and msw-agent Stage 2+ work being stable.

---

## Related docs

- `IMPLEMENTATION_PLAN.md` — gap table (task-level status tracker)
- `MASTER_PLAN.md` — architecture principles (authoritative)
- `PLAN_namespace_unification.md` — NamespaceBuilder + namespace.msw.yaml (Sprint 1+2 done; Sprint 3 = msw-namespace extraction, pending decision 1)
- `PLAN_external_packages.md` — build system audit for external/ repos
- `PLAN_org_migration_tracker.md` — repo transfer status (larsrollik/ → MurineShiftWork/)
