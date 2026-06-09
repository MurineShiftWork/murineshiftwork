# MSW Package Graph

*Created 2026-05-30. Captures expected final package graph and open naming/scope decisions.*
*Supersedes §4 of `IMPLEMENTATION_PLAN.md` for package graph design; gap-table status tracking stays there.*

---

## Package hierarchy

```
msw-core                             ← acquisition stack; always installed on rigs
  cli/                               ← argparse entrypoints; task discovery via entry-points
  hardware/                          ← Bpod, PulsePal, scale, camera, stage, parent session
  hooks/                             ← pre/post session hooks
  logic/                             ← TaskProcess, config, barcode, IO, calibration, maths
  namespace/                         ← session path building, MSW file naming, manifest

msw-agent                            ← [agent] opt-in extra
  logagent/                          ← FastAPI ingest server + LogAgent daemon

msw-readers                          ← [readers] opt-in extra
  readers/                           ← session readers, batch API, alignment

msw-tasks-core                       ← [tasks] core; calibration + hardware test tasks
  tasks/calibration/
  tasks/_test_*/  (no cross-task imports)

msw-tasks-sequence                   ← [tasks-sequence]; reference task for external authors
  tasks/sequence/

msw-tasks-tab                        ← lab-specific; separate repo, not on PyPI
  tasks/probabilistic_switching/
  tasks/probabilistic_switching_fixedsubjects/
  tasks/optotagging/
  tasks/airpuff/
  tasks/exp_trn_spindle/
  tasks/periodic_trigger/
  tasks/periodic_trigger_with_video/
  tasks/openfield/                   ← thin wrapper; delegates to periodic_trigger_with_video
  tasks/sleep_homecage/              ← thin wrapper; delegates to periodic_trigger_with_video
  tasks/_test_trigger_with_video/    ← must move here (imports periodic_trigger_with_video)
  tasks/_test_video/                 ← must move here or delete (imports probabilistic_switching)
```

### Dependency graph

```
msw-tasks-tab      → msw-core, acquisition-namespace, ttl-barcoder
msw-tasks-sequence → msw-core, acquisition-namespace, ttl-barcoder
msw-tasks-core     → msw-core, acquisition-namespace
msw-readers        → msw-core, acquisition-namespace, ttl-barcoder, pydantic, pandas
msw-agent          → (stdlib + fastapi only; zero MSW imports)
msw-core           → acquisition-namespace, ttl-barcoder, pypulsepal, one-axis-stage, …
```

No circular deps. `msw-tasks-tab` and `msw-tasks-sequence` both depend on `msw-core` only;
they do not depend on each other. External task packages follow the same pattern.

### Standalone packages (MurineShiftWork org)

```
acquisition-namespace   pypulsepal        ttl-barcoder
rpi-camera-ensemble     msw-flir-bonsai   one-axis-stage
serial-scale-bench      serial-scale-hx711  rfid-to-url
msw-oe                  ← OE plugin (entry-point group; separate repo, not yet created)
```

### `murineshiftwork` metapackage extras

| Extra | Pulls in |
|---|---|
| *(base)* | `msw-core` + `acquisition-namespace` + `ttl-barcoder` |
| `[tasks]` | `msw-tasks-core` + `msw-tasks-sequence` |
| `[readers]` | `msw-readers` |
| `[agent]` | `msw-agent` |
| `[flir]` | `msw-flir-bonsai` |
| `[rce]` | `rpi-camera-ensemble` |
| `[calibration]` | `serial-scale-hx711`, `serial-scale-bench` |
| `[labwatch]` | `msw-labwatch` |
| `[dev]` | pytest, ruff, mypy, … |
| `[docs]` | mkdocs-material |

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

## Locked decisions (2026-06-02)

### 1. No `msw-namespace` package — absorbed into `msw-core`

`msw-namespace` will NOT be extracted as a standalone package.
The MSW namespace layer (`namespace/`, including `NamespaceBuilder` usage,
`namespace.msw.yaml`, `parse_session_basename`, `is_msw_file`) is
MSW-specific and belongs inside `msw-core`.

`acquisition-namespace` remains the only general-purpose namespace dep.
It is not extended with MSW-specific constants or parsing logic.

PLAN_namespace_unification.md Sprint 3 (msw-namespace extraction) is cancelled.

---

### 2. Package name: `msw-core`; scope includes `namespace/`

`msw-logic` → **`msw-core`** (confirmed rename).

Scope: `logic/` + `hardware/` + `namespace/`.
Python import paths (`murineshiftwork.logic.*`, `murineshiftwork.hardware.*`,
`murineshiftwork.namespace.*`) are unchanged — no new root namespace.

---

### 3. Task package split: `msw-tasks-core`, `msw-tasks-sequence`, external repo for the rest

- **`msw-tasks-core`**: calibration tasks + hardware test tasks only. Minimal
  deps; ships with the main install as the reference task set.
- **`msw-tasks-sequence`**: sequence task, extracted as its own package.
  Self-contained enough to serve as an example for external task authors.
- **Everything else** (probabilistic_switching, fixedsubjects, optotagging,
  airpuff, spindle, periodic): moves to a separate `msw-tasks-lab` repo
  (or similar) outside the main org. Not a PyPI requirement; installed
  directly by the lab.
- **Goal**: anyone can author and install their own task package alongside
  `msw-core` without forking the main repo. `msw-tasks-core` + `msw-tasks-sequence`
  are the published reference implementations that show the pattern.

`[tasks]` extra on the metapackage pulls `msw-tasks-core` + `msw-tasks-sequence`.
Lab-specific tasks are installed separately (`pip install ./msw-tasks-lab`).

---

### 4. `msw-agent` is `[agent]` opt-in extra

`msw-agent` stays an opt-in `[agent]` extra.
`msw-core` (task_process.py) guards the LogAgent import with `try/ImportError`
so the relay is silently disabled when the package is absent.
Analysis machines and CI installs stay lean (no FastAPI/uvicorn in base).

---

## Task isolation roadmap item

Tasks are currently coupled to `TaskProcess` internals for two concerns:

1. **Trial data save** — tasks call `save_trial_data()` directly from `logic/io.py`.
   Goal: `TaskProcess` owns the write (via a registered writer); tasks emit
   trial dicts into a result callback; the writer is swappable (JSONL today,
   anything tomorrow). Relates to the `TrialDataWriter` ABC item in ROADMAP.

2. **Log dispatch / relay** — only `sequence` calls `relay_queue.put_nowait()`.
   Goal: `TaskProcess` hooks the relay; tasks call a generic `emit_trial(dict)`
   method on their context object without knowing about queues or HTTP.

Both are prerequisites for a task definition language that is hardware-agnostic
and backend-replaceable (Bpod today, NI-DAQ or Teensy tomorrow).

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

## Extraction order

1. `msw-tasks-core` (calibration + test tasks; minimal deps — good first split test)
2. `msw-tasks-sequence` (self-contained reference task; validates task packaging pattern)
3. `msw-core` (`logic/` + `hardware/` + `namespace/` + `hooks/`; unblocks readers and agent)
4. `msw-agent` (already structurally isolated; import guard already in place)
5. `msw-readers` (no hardware deps; needs `msw-core` for namespace imports)
6. `msw-tasks-lab` (lab-specific tasks; separate repo, not a PyPI requirement)

---

## Extraction blockers — from boundary review (2026-06-02)

**Blocker for step 1 (`msw-tasks-core`):**

Two test tasks have cross-task imports into lab tasks and cannot be extracted into `msw-tasks-core` as-is:

- `tasks/_test_trigger_with_video/...:1` — entire file is a re-import of `periodic_trigger_with_video.run_task`. → Delete; the base task can be run directly via CLI flags.
- `tasks/_test_video/_test_video.py:11` — imports `OnlinePlottingForPS` from `probabilistic_switching`. → Remove the plot import; `_test_video` does not need a real renderer.

**Scope gap:**

- `hooks/` was missing from the `msw-core` scope; now included explicitly in step 3 above.

**Prerequisite for all task extraction — CLI task discovery:**

`list_available_tasks()` and `find_task_by_name()` in `logic/misc.py` currently walk
the filesystem at `murineshiftwork/tasks/`. Once tasks are in separate installed packages
there is no single directory to walk.

Required change before any task package can be extracted:

1. Each task package declares an entry point in its `pyproject.toml`:
   ```toml
   [project.entry-points."msw.tasks"]
   sequence = "murineshiftwork.tasks.sequence.sequence:run_task"
   ```
2. `list_available_tasks()` is rewritten to use `importlib.metadata.entry_points(group="msw.tasks")`.
3. `find_task_by_name()` resolves against that registry instead of a path scan.
4. Move both functions from `logic/misc.py` to `cli/tasks.py` (they are CLI concerns, not logic).

---

## Related docs

- `IMPLEMENTATION_PLAN.md` — gap table (task-level status tracker)
- `MASTER_PLAN.md` — architecture principles (authoritative)
- `PLAN_namespace_unification.md` — NamespaceBuilder + namespace.msw.yaml (Sprint 1+2 done; Sprint 3 = msw-namespace extraction, pending decision 1)
- `PLAN_external_packages.md` — build system audit for external/ repos
- `PLAN_org_migration_tracker.md` — repo transfer status (larsrollik/ → MurineShiftWork/)
