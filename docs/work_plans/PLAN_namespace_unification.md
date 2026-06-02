# Namespace Unification Plan

*Created 2026-05-23. **Option B implemented 2026-05-27** — `generate_session_paths()` is now a thin wrapper over `NamespaceBuilder`; mandatory acquisition level added; `session_folder_relative` + `acquisition_name` in session_paths dict. See commit `449a36a`.*

---

## Status: Option B complete

All three sprint blocks below are done. The remaining work is the manifest writer and reader dispatch
(tracked in `PLAN_session_manifests.md` and `PLAN_retrograde_reader.md`).

---

## Problem statement (resolved)

The codebase previously had three parallel, unconnected systems doing overlapping jobs:

| System | File | What it does |
|---|---|---|
| `generate_session_paths()` | `namespace/paths.py` | Hardcoded `{subject}__{datetime}__{task}` path builder; returns a dict |
| `NamespaceBuilder` + YAML specs | `namespace/spec.py` + `namespace.v*.yaml` | General-purpose YAML-driven path builder with hierarchy, templates, regex — not used in the operational session path generation |
| `msw_files.py` | `namespace/msw_files.py` | Standalone artifact registry + `msw_file()` builder — not yet wired to either above |

The `.msw.` separator and artifact names were scattered as raw string literals across `task_process.py`, `log.py`, and every task file.  There was no single definition of what the separator is or what files are valid.

---

## Key observations

### NamespaceBuilder YAML specs vs. operational paths

The `namespace.v1/v2/v3.yaml` specs describe a different naming convention (`{subject_prefix}{subject_id}_{exp_short_name}_m{mouse_id}...`) than what `generate_session_paths()` actually writes (`{subject}__{datetime}__{task}`).  These are **orthogonal** naming schemes for different lab setups.  They coexist and should not be merged.

What's missing is an **MSW operational spec** — a YAML that describes the actual `{subject}__{datetime}__{task}` convention that the software uses, with `msw_separator` and `core_artifacts` included.

### NamespaceBuilder standalone potential

`NamespaceBuilder` depends only on pydantic, yaml, re, pathlib — no MSW-specific imports.  It can be extracted to a standalone package (`msw-namespace`) once:
1. The operational MSW spec is a proper YAML file (not hardcoded Python)
2. `generate_session_paths()` is a thin wrapper over `NamespaceBuilder`
3. `NamespaceBuilder` has the three artifact methods (`get_artifact_file`, `is_msw_file`, `extract_artifact`)

---

## Design decision: Option A (immediate) vs Option B (full)

### Option A — Extend NamespaceSpec, keep `generate_session_paths()` as-is

Minimal change.  `NamespaceSpec` gains two new optional fields:

```python
class NamespaceSpec(BaseModel):
    ...
    msw_separator: str = ".msw."
    core_artifacts: list[str] = []
```

`NamespaceBuilder` gains three new methods:

```python
builder.get_artifact_file(session_file_path, artifact) -> Path
    # core artifact: validated against core_artifacts list
    # unknown artifact: allowed through (task extension) — no error
builder.is_msw_file(path) -> bool
builder.extract_artifact(path) -> str
```

`generate_session_paths()` instantiates a shared `NamespaceBuilder` with an embedded MSW spec dict and uses it internally to build `session_yaml` and `session_log` keys.

All callers (`task_process.py`, `log.py`) use `builder.get_artifact_file()` instead of raw string concatenation.  Task files use `builder.get_artifact_file(out_path, "jsonl")` etc.

**Scope**: 2 sprints — (1) extend spec + NamespaceBuilder methods, (2) update callers + tests.

**Standalone ready?** Not yet — spec is still embedded in Python code, not a YAML file.

---

### Option B — Full unification: `generate_session_paths()` via NamespaceBuilder + MSW YAML spec

Create `namespace/namespace.msw.yaml` that defines the operational MSW namespace:

```yaml
version: "msw-1"
description: "MSW operational session namespace"
msw_separator: ".msw."
core_artifacts:
  - session.yaml
  - plot_spec.yaml
  - log
  - jsonl
  - df.jsonl
  - df.pkl
  - csv
  - stimulation.json
hierarchy:
  - subject
  - session
levels:
  subject:
    template: "{subject}"
    regex: "(?P<subject>[\\w\\-]+)"
    optional_fields: []
  session:
    template: "{subject}__{datetime}__{task}"
    regex: "(?P<subject>.+)__(?P<datetime>\\d{8}_\\d{6}(?:_\\d{6})?)__(?P<task>[\\w\\-]+)"
    optional_fields: []
```

`generate_session_paths()` becomes a thin shim:

```python
_MSW_BUILDER = NamespaceBuilder.from_yaml(Path(__file__).parent / "namespace.msw.yaml")

def generate_session_paths(subject, task, basepath, ...):
    dt = datetime.now().strftime(...)
    values = {"subject": subject, "task": task, "datetime": dt}
    session_basename = _MSW_BUILDER.build_path("session", values)
    session_folder = Path(basepath) / subject / session_basename
    base = str(session_folder / session_basename)
    return {
        "session_basename": session_basename,
        "session_folder": str(session_folder),
        "session_file_path": base,
        "session_yaml": str(_MSW_BUILDER.get_artifact_file(base, "session.yaml")),
        "session_log":  str(_MSW_BUILDER.get_artifact_file(base, "log")),
        ...
    }
```

Reader uses `_MSW_BUILDER.is_msw_file()`, `_MSW_BUILDER.extract_artifact()`.

**Scope**: 1 additional sprint after Option A — refactor `paths.py` + add MSW YAML + update reader.

**Standalone ready?** Yes — after Option B, `NamespaceBuilder` + the YAML is everything needed.

---

## Implementation status

```
Sprint 1 (ft/namespace-unification) — DONE:
  [x] msw_files.py — kept as thin convenience wrapper (msw_file(), is_msw_file(), msw_artifact())
  [x] namespace.msw.yaml created — operational MSW spec: subject/acquisition/session/file hierarchy
  [x] generate_session_paths() is now a thin wrapper over NamespaceBuilder
  [x] Acquisition level mandatory (optional_levels: []); standalone gets subject__dt__session_{task}
  [x] level_overrides added to NamespaceBuilder.generate_path() for external parent names (OE)
  [x] session_folder_relative + acquisition_name added to session_paths dict
  [x] session_basename_behav removed; inlined at Bpod call site
  [x] All conductor initialize_acquisition() calls use session_folder_relative
  [x] v1/v2/v3 YAML duplicates removed from src/namespace/; test fixtures in tests/data/
  [x] test_namespace_builder.py, test_namespace.py, test_msw_files.py updated

Sprint 2 (same branch) — DONE as part of Sprint 1:
  [x] namespace/namespace.msw.yaml shipped with package
  [x] generate_session_paths() routes all path construction through NamespaceBuilder

Sprint 3 (ft/namespace-standalone — future):
  [ ] Extract NamespaceBuilder to msw-namespace package (pyproject.toml split)
  [ ] murineshiftwork depends on msw-namespace; installs namespace.msw.yaml as package data
  [ ] Currently: acquisition-namespace is the external package (in external/); once published
      to PyPI as a dependency, the external/ copy is dropped

## What remains

- Session/acquisition manifest writer: see PLAN_session_manifests.md
- Reader dispatch skeleton: see PLAN_retrograde_reader.md §Phase 2b
- Opto per-subprotocol JSONL split: see PLAN_session_manifests.md
```

---

## Artifact extension model

Core artifacts are defined in `core_artifacts` in the spec.  Task-specific artifacts (e.g. `"stimulation.json"`, `"df.jsonl"`) are allowed through without error or warning — the registry is open.  Readers add all discovered `.msw.{artifact}` files to the session dict without complaints.

The only validation: `get_artifact_file(base, artifact)` raises `ValueError` if the artifact contains the separator (`.msw.`) itself — that would create a malformed double-namespace filename.

---

## Reader integration notes

Current reader behaviour:
- `readers/namespace.py`: `".msw." in file` checks — replace with `builder.is_msw_file(file)`
- `readers/session.py`: `s.split(".msw.")[-1]` — replace with `builder.extract_artifact(s)`
- Both currently use raw string literals for the separator; both change in Sprint 2

Reader should NOT validate artifact names against `core_artifacts` — it sees whatever the task wrote, logs an unknown at DEBUG only if helpful, and adds it to the session dict.

---

## Open question

**`session_basename_behav`** (`{basename}.msw`) — the Bpod workspace file name.
This is NOT a `.msw.{artifact}` file; it IS the base that artifact files extend from.
It predates this design and may be renamed to `session_bpod_base` or similar in Sprint 2
to disambiguate.  Deferred.
