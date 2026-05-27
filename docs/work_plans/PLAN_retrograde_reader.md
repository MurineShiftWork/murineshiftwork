# Retrograde Reader Framework

**Status:** Phase 1 done (detection + validation layer). Phase 2b (reader dispatch) in progress — see sprint item 8 in ROADMAP.md.

---

## Why this exists

Every session MSW has ever written is on disk.  The artifact format and basename datetime precision have changed at least three times.  Any analysis pipeline, calibration reader, or session browser must load sessions regardless of when they were written.  This doc captures the full format matrix, what is implemented, and what must still be done to close the gap.

---

## Format matrix

Two orthogonal dimensions describe every session on disk.

### Dimension 1 — Namespace version (basename datetime precision)

| Version constant | Datetime field | Example |
|---|---|---|
| `NAMESPACE_LEGACY` | `YYYYMMDD_HHMMSS` (seconds) | `t004_...__20260429_153653__...` |
| `NAMESPACE_V1` | `YYYYMMDD_HHMMSS_ffffff` (µs) | `t012_...__20260508_172956_258756__...` |

Detection: `parse_session_basename(basename)` tries V1 regex first (longer match), falls back to LEGACY.  Returns `namespace_version` in result dict.

### Dimension 2 — Artifact format (settings storage layout)

| Constant | Files present | Era |
|---|---|---|
| `ARTIFACT_FORMAT_LEGACY` | `task_settings.py` + `switching.pkl` / `switching.csv` — no `.msw.` segment | Pre-2022 ceph sessions |
| `ARTIFACT_FORMAT_SEPARATE_JSON` | `.msw.settings.process.json` + `.msw.settings.task.json` + `.msw.df.pkl` or `.df.jsonl` | 2025-04 → 2026-05-20 |
| `ARTIFACT_FORMAT_SESSION_YAML` | `.msw.session.yaml` (msw\_format\_version: 2) + `.msw.df.jsonl` | 2026-05-20 onwards (current) |

Detection: `detect_artifact_format(session_dir)` checks file names in order: legacy markers → `session.yaml` → `settings.process.json`.

### Combined matrix across all known eras

| Era | `namespace_version` | `artifact_format` | `msw_version` value | Data location |
|---|---|---|---|---|
| ceph 2021 | `NAMESPACE_LEGACY` | `ARTIFACT_FORMAT_LEGACY` | `"legacy"` | `/ceph/sjones/users/lars/data/s008_*/...` |
| maindata 2025-04 | `NAMESPACE_LEGACY` | `ARTIFACT_FORMAT_SEPARATE_JSON` | `"< 1.0.0"` | `/mnt/maindata/data/_test_subject/__2025*` |
| maindata 2026-05 early | `NAMESPACE_V1` | `ARTIFACT_FORMAT_SEPARATE_JSON` | `"1.0.0"` | `/mnt/maindata/data/t012_*/...` |
| maindata 2026-05 current | `NAMESPACE_V1` | `ARTIFACT_FORMAT_SESSION_YAML` | `"x.y.z"` semver | `/mnt/maindata/data/t013_*/...` (recent) |

### Third dimension — directory depth (added 2026-05-27)

The mandatory acquisition level added in commit `449a36a` introduces a third structural dimension:

| Depth | Structure | Era |
|---|---|---|
| 2 levels (`subject/session/`) | Legacy — no acquisition dir | All sessions before 2026-05-27 |
| 3 levels (`subject/acquisition/session/`) | Current — acquisition always present | Sessions from 2026-05-27 onwards |

**Reader impact:** `read_session_data(session_dir)` always receives a session dir (not an acquisition dir), so the depth difference is invisible to the reader. What changes is how callers (scripts, post-processing, the future session browser) navigate to find session dirs — they now must descend through the acquisition level.

`detect_session_format()` already handles depth-2 and depth-3 correctly: it scans files in the provided `session_dir` regardless of what's above it.

A future `read_acquisition()` function will:
1. Accept an acquisition dir (depth-3 root)
2. Read `acquisition_manifest.yaml` to enumerate sessions
3. Call `read_session_data()` for each session
4. Return a keyed dict of session data dicts

See `PLAN_session_manifests.md` for the manifest format.

The `msw_version` value `"< 1.0.0"` means the process JSON exists but predates the `msw_version` key.  `"legacy"` means no process JSON at all.

---

## What is implemented (Phase 1)

### `src/murineshiftwork/readers/namespace.py`

Three new public symbols alongside the existing `test_is_*` helpers:

```python
ARTIFACT_FORMAT_LEGACY        = "legacy"
ARTIFACT_FORMAT_SEPARATE_JSON = "separate_json"
ARTIFACT_FORMAT_SESSION_YAML  = "session_yaml"

detect_artifact_format(session_dir) -> str
    # Returns one of the constants above based on file presence.

detect_session_format(session_dir) -> dict
    # Returns: basename, namespace_version, artifact_format, parse_error
    # Uses _infer_session_basename() to extract basename from .msw. filenames
    # (works for real sessions where dir name == basename AND for test fixtures
    # with generic dir names like fixture_pkl/).

validate_session_namespace(session_dir) -> dict
    # Returns: valid, namespace_version, basename, error
    # Validates basename against NamespaceBuilder regex (acquisition-namespace).
```

Private `_infer_session_basename(session_dir)`: scans files for `.msw.` and returns the prefix.  Falls back to `session_dir.name` for legacy sessions (no `.msw.` files) — works because real session dirs are named after the session basename.

### `tests/test_reader_session_format.py`

38 parametrized tests covering all 5 present fixtures.  Adding a new fixture = one line in `FIXTURE_EXPECTATIONS`.

```python
FIXTURE_EXPECTATIONS = [
    ("fixture_pkl",          NAMESPACE_LEGACY, ARTIFACT_FORMAT_SEPARATE_JSON),
    ("fixture_jsonl",        NAMESPACE_V1,     ARTIFACT_FORMAT_SEPARATE_JSON),
    ("fixture_v2",           NAMESPACE_V1,     ARTIFACT_FORMAT_SESSION_YAML),
    ("fixture_fixedsubjects",NAMESPACE_V1,     ARTIFACT_FORMAT_SESSION_YAML),
    ("fixture_sequence",     NAMESPACE_V1,     ARTIFACT_FORMAT_SESSION_YAML),
]
```

### Ceph legacy sessions — detection confirmed

The two ceph file naming styles both resolve correctly:

- `s008` style: `task_settings.py` (no session prefix) → `endswith("task_settings.py")` ✓
- `s001` style: `LBR__...probabilistic_switching.task_settings.py` → same check ✓; `.pkl` → `endswith("switching.pkl")` ✓

`_infer_session_basename()` returns None (no `.msw.` files) → fallback to dir name (e.g., `s008_tab_m1113182_LR__20210707_143042__probabilistic_switching`) → parses as `NAMESPACE_LEGACY` ✓

---

## Phase 2 — what must still be done

### 2a. Add `fixture_legacy` (URGENT — gap in CI coverage)

No test covers `ARTIFACT_FORMAT_LEGACY` detection.  Source sessions exist on ceph.

```
# Copy one real session to tests/data/fixture_legacy/
cp -r /ceph/sjones/users/lars/data/s008_tab_m1113182_LR/\
s008_tab_m1113182_LR__20210707_143042__probabilistic_switching/ \
tests/data/fixture_legacy/
```

Then add one line to `FIXTURE_EXPECTATIONS`:

```python
("fixture_legacy", NAMESPACE_LEGACY, ARTIFACT_FORMAT_LEGACY),
```

Notes:
- The `task_settings.py` inside these sessions is a Python module with `SETTINGS = {...}` — already handled by `read_settings_py()` in `readers/files.py`
- The `.pkl` file is a raw pybpod pandas DataFrame — handled by `read_trial_df()`
- `is_complete_session` check must NOT require `settings.process` for legacy sessions (already gated by `is_legacy_session` in `session.py`)

### 2b. Refactor `read_session_data()` to detect-then-dispatch (URGENT)

The current function uses implicit branching over a flat file-key dict.  This is fragile and extends poorly.

**Target design:**

```python
_READER_DISPATCH = {
    ARTIFACT_FORMAT_SESSION_YAML:  _read_session_yaml,
    ARTIFACT_FORMAT_SEPARATE_JSON: _read_separate_json,
    ARTIFACT_FORMAT_LEGACY:        _read_legacy,
}

def read_session_data(session_dir, load_raw=False, **kwargs):
    fmt = detect_session_format(session_dir)
    reader = _READER_DISPATCH.get(fmt["artifact_format"])
    if reader is None:
        raise ValueError(f"No reader for format: {fmt['artifact_format']!r}")
    data = reader(Path(session_dir), fmt, load_raw=load_raw, **kwargs)
    # normalise: attach format metadata at top level
    data["namespace_version"] = fmt["namespace_version"]
    data["artifact_format"]   = fmt["artifact_format"]
    return data
```

Each private reader (`_read_session_yaml`, `_read_separate_json`, `_read_legacy`) takes `(session_dir, fmt, **kwargs)` and returns a dict conforming to the existing schema (`df`, `raw`, `settings.task`, `settings.process`, `msw_version`, `is_complete_session`, `is_legacy_session`, `is_ephys_session`).

Output schema contract is unchanged — callers see identical keys regardless of which reader ran.

### 2c. Urgent bug: `is_complete_session` always False for v2+ sessions

`required_file_keys` in `session.py` line ~117 includes `"raw"` but v2+ sessions never write a raw CSV.  Remove `"raw"` from required keys (or make it optional only when a CSV file is present in the dir).

Fix location: `src/murineshiftwork/readers/session.py` line ~117.

### 2d. Expose `artifact_format` and `namespace_version` at top level of `read_session_data()` output

After the dispatch refactor, these are always available from `detect_session_format()`.  They should be surfaced in the return dict so callers can branch without re-detecting.  Currently `is_legacy_session` (bool) is the only format indicator — insufficient for 4-tier format matrix.

---

## Namespace YAML versioning strategy

**Key principle: `namespace.msw.yaml` is write-time only.  Old sessions are never validated through the builder during reads.**

The builder is used for:
1. `build_path("session", values)` — writing new session basenames
2. `extract_level_values("session", name)` — parsing/validating a known-current basename
3. `build_path("file", values)` / `extract_level_values("file", name)` — artifact filename construction

Reading old sessions uses `detect_artifact_format()` + format-specific reader functions.  The builder is not involved.

### Session basename structure — treat as immutable

`{subject}__{datetime}__{task}` is the primary identity key for every session ever written.  Do not add mandatory new fields.  The `(?:_\d{6})?` optional group in the datetime regex already handles both LEGACY and V1 — this is already backward-compatible.

### Artifact format evolution — use `msw_format_version` inside `session.yaml`

A future `msw_format_version: 3` needs a branch inside `_read_session_yaml()` only.  The YAML file itself does not need to change.

### If `namespace.msw.yaml` must be changed

| Change type | Action |
|---|---|
| File-level regex/template change (e.g., new artifact separator) | Update YAML + update `_infer_session_basename()` to still return old basenames correctly |
| Session-level template changes (new mandatory basename field) | Create `namespace.msw.v2.yaml`; update `get_msw_builder(version=None)` to accept a version argument; store `namespace_spec_version` in `session.yaml` |
| Artifact format fields change | Increment `msw_format_version` in the YAML content; add reader branch in `_read_session_yaml()` |

**Recommendation: Option A (single living YAML) for the foreseeable future.**  Session basename structure is frozen.  Artifact format evolution goes through `msw_format_version`.  Only version the YAML file (`v2.yaml`) if a truly new mandatory basename field is ever required — which should be avoided by design.

---

## File locations

| File | Role |
|---|---|
| `src/murineshiftwork/readers/namespace.py` | Format constants + detection functions |
| `src/murineshiftwork/readers/session.py` | Reader (needs dispatch refactor) |
| `src/murineshiftwork/namespace/namespace.msw.yaml` | Current write spec (v2.0) |
| `src/murineshiftwork/namespace/paths.py` | `parse_session_basename()`, `generate_session_paths()`, `get_msw_builder()` |
| `tests/test_reader_session_format.py` | Parametrized detection + validation tests |
| `tests/test_reader_fixtures.py` | Reader integration tests (fixture_pkl + fixture_jsonl) |
| `tests/test_reader_v2.py` | Reader integration tests (fixture_v2 + fixture_jsonl back-compat) |
| `tests/test_reader_task_fixtures.py` | Task-specific fixtures (fixture_sequence, fixture_fixedsubjects) |
| `tests/data/fixture_pkl/` | `NAMESPACE_LEGACY` + `ARTIFACT_FORMAT_SEPARATE_JSON` (no `msw_version` key) |
| `tests/data/fixture_jsonl/` | `NAMESPACE_V1` + `ARTIFACT_FORMAT_SEPARATE_JSON` (has `msw_version` key) |
| `tests/data/fixture_v2/` | `NAMESPACE_V1` + `ARTIFACT_FORMAT_SESSION_YAML` |
| `tests/data/fixture_fixedsubjects/` | `NAMESPACE_V1` + `ARTIFACT_FORMAT_SESSION_YAML` |
| `tests/data/fixture_sequence/` | `NAMESPACE_V1` + `ARTIFACT_FORMAT_SESSION_YAML` |
| `tests/data/fixture_legacy/` | **MISSING** — copy from ceph (see §2a) |

---

## Related plans

- `PLAN_oe_remote.md` — `msw oe` subcommand + namespace wiring (uses `extract_level_values` / `build_path` roundtrip for OE base_text validation)
- `IMPLEMENTATION_PLAN.md` — namespace split into sub-packages (readers will be in `msw-logic`)
