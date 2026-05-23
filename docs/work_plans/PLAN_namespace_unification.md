# Namespace Unification Plan

*Created 2026-05-23. Branch target: ft/namespace-unification.*
*Pre-requisite: ft/extras-restructure (see MASTER_PLAN) must land first — it defines which install
extras provide fastapi/httpx and restructures CI matrix variants.*

---

## Problem statement

The codebase has three parallel, unconnected systems doing overlapping jobs:

| System | File | What it does |
|---|---|---|
| `generate_session_paths()` | `namespace/paths.py` | Hardcoded `{subject}__{datetime}__{task}` path builder; returns a dict |
| `NamespaceBuilder` + YAML specs | `namespace/spec.py` + `namespace.v*.yaml` | General-purpose YAML-driven path builder with hierarchy, templates, regex — not used in the operational session path generation |
| `msw_files.py` | `namespace/msw_files.py` | Standalone artifact registry + `msw_file()` builder — not yet wired to either above |

The `.msw.` separator and artifact names are scattered as raw string literals across `task_process.py`, `log.py`, and every task file.  There is no single definition of what the separator is or what files are valid.

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

## Recommended sequence

```
Sprint 1 (ft/namespace-unification):
  [x] msw_files.py already created — DELETE it; merge into NamespaceBuilder
  [ ] Add msw_separator + core_artifacts to NamespaceSpec (Pydantic + YAML optional fields)
  [ ] Add get_artifact_file(), is_msw_file(), extract_artifact() to NamespaceBuilder
  [ ] Update existing namespace.v1/v2/v3.yaml — add msw_separator field (with default .msw.)
  [ ] generate_session_paths(): use NamespaceBuilder instance for artifact methods; add
      session_yaml + session_log pre-built keys to returned dict
  [ ] Update task_process.py + log.py to use builder methods (no raw string concat)
  [ ] Update test_namespace.py + test_namespace_builder.py for new methods
  [ ] Pre-commit + all tests green

Sprint 2 (same branch or ft/namespace-msw-yaml):
  [ ] Create namespace/namespace.msw.yaml — operational MSW spec with msw_separator +
      core_artifacts + hierarchy + levels for {subject}__{datetime}__{task}
  [ ] Refactor generate_session_paths() to thin wrapper over _MSW_BUILDER
  [ ] Update reader (readers/namespace.py, readers/session.py) to use
      _MSW_BUILDER.is_msw_file() / extract_artifact() instead of raw string checks
  [ ] Update all task files (airpuff, optotagging, exp_trn_spindle, sequence/task_objects)
      to call builder.get_artifact_file() — remove all raw ".msw." concatenation
  [ ] Pre-commit + all tests green

Sprint 3 (ft/namespace-standalone — future):
  [ ] Extract NamespaceBuilder to msw-namespace package (pyproject.toml split)
  [ ] murineshiftwork depends on msw-namespace; installs namespace.msw.yaml as package data
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
