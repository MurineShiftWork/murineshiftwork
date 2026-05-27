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

---

## Fourth dimension — manifest-enabled sessions (2026-05-27)

A new structural sub-type of `ARTIFACT_FORMAT_SESSION_YAML` emerged in production on 2026-05-27.  Not a new format constant — still detected as `session_yaml` — but introduces two optional companion files:

### `acquisition_manifest.yaml` (acquisition-dir level)

```yaml
msw_manifest_version: 1
type: acquisition
acquisition_name: _test_oe_controller__20260527_132639__ephys
sessions:
  - basename: _test_subject__20260527_133053_901389__optotagging
    started_at: '2026-05-27T12:30:53+00:00'
    ended_at: '2026-05-27T12:31:33+00:00'
    status: complete      # complete | running | aborted
  - basename: _test_subject__20260527_135402_976801__optotagging
    started_at: '2026-05-27T12:54:02+00:00'
    ended_at: null
    status: running
```

Consumed by `load_acquisition()` (Phase 3) to enumerate sessions with status + timestamps.  Currently ignored by `read_session_data()`.

### `session_manifest.yaml` (session-dir level)

```yaml
msw_manifest_version: 1
type: session
session_basename: _test_subject__20260527_133053_901389__optotagging
subprotocols:
  - name: power_ramp_1mw
    file: _test_subject__...optotagging_power_ramp_1mw.msw.df.jsonl   # flat or subdir path
    barcode_start: 130617617295   # integer barcode value for ephys alignment
    barcode_end:   130617640698
    status: complete
  - name: power_ramp_2mw
    file: power_ramp_2mw/_test_subject__...optotagging_power_ramp_2mw.msw.df.jsonl
    barcode_start: 130617650423
    barcode_end: null
    status: aborted
```

Subprotocol JSONL files may be flat (session dir) or in subdirs named after the subprotocol.  `_msw_files_dict` only scans `glob("*")` — non-recursive — so subdir files are invisible without the manifest.  For flat multi-protocol files, the same `"df.jsonl"` key collision means only one file would be found without the manifest.

### `parent_acquisition` block in `.msw.session.yaml`

```yaml
parent_acquisition:
  backend: open_ephys
  acquisition_name: _test_oe_controller__20260527_132639__ephys
  subject: _test_oe_controller
  parent_directory: D:\DATA
  oe_session_name: _test_oe_controller__20260527_132639__pxi
  status: IDLE
```

**Already extracted** as `data["settings.ephys"]` — fix landed 2026-05-27.  `is_ephys_session` now works correctly for SESSION_YAML sessions.

### Multi-protocol loading design (Phase 3b)

When `session_manifest.yaml` is present, `_read_session_yaml` should:

1. Read the manifest to enumerate subprotocols + file paths
2. For each subprotocol: resolve path relative to `session_dir`; call `read_trial_df()`
3. Add a `"subprotocol"` column to each subprotocol DataFrame
4. `pd.concat(subprotocol_dfs, ignore_index=True)` → `data["df"]`
5. Store manifest subprotocols list as `data["subprotocols"]` (metadata, not trial data)
6. Subprotocols with `status: running` or `status: aborted` are still loaded if file exists; completeness flag reflects whether all subprotocols are `complete`

If no `session_manifest.yaml`: current behaviour (load single JSONL/PKL) is unchanged.

---

## Phase 2 status (2026-05-27)

| Sub-task | Status |
|---|---|
| 2a. `fixture_legacy` copy from ceph | **In progress** — user is copying s080–s090 sessions to `tests/data/`; add one line to `FIXTURE_EXPECTATIONS` when done |
| 2b. `_READER_DISPATCH` refactor | **DONE** · 2026-05-27 |
| 2c. `is_complete_session` `"raw"` key bug | **DONE** · 2026-05-27 — `raw` / `load_raw` removed from `session.py` entirely |
| 2d. `artifact_format` + `namespace_version` at top level | **DONE** · 2026-05-27 |

---

## Phase 3 — Full reader interface

### Package placement decision

**Stay in `murineshiftwork` core.**  The IMPLEMENTATION_PLAN already names `msw-readers` as a future extraction target.  Extracting now, before the interface is stable and before the monolith split begins, adds churn with no gain.  Design the interface to be extraction-ready: no imports from `tasks/`, `hardware/`, or `cli/` inside `readers/`; clean module boundary preserved.

When extracted, `msw-readers` will depend only on: `acquisition-namespace`, `ttl-barcoder`, `pandas`, `pyyaml`.  Zero hardware deps.

---

### 3a. `MswSession` dataclass

Replace the plain dict return from `read_session_data()` with a structured object.  The dict path remains for backward compat (internal callers); `load_session()` is the new public entry point.

```python
# src/murineshiftwork/readers/models.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import pandas as pd

@dataclass
class MswSession:
    # Identity
    session_dir:       Path
    basename:          str
    subject:           str
    datetime:          datetime
    task:              str
    # Format provenance
    namespace_version: str            # "v1" | "legacy"
    artifact_format:   str            # ARTIFACT_FORMAT_* constant
    msw_version:       str            # semver | "legacy" | "< 1.0.0"
    # Content
    df:                pd.DataFrame | None
    settings_task:     dict
    settings_process:  dict | None
    settings_stage:    dict | None
    settings_ephys:    dict | None    # parent_acquisition block from session.yaml
    # Flags
    is_complete:       bool
    is_ephys:          bool
    # Optional: acquisition context (populated by load_acquisition)
    acquisition_name:  str = ""
    acquisition_dir:   Path | None = None
```

`load_session(session_dir) -> MswSession` wraps `read_session_data()` and maps the dict onto the dataclass.  It also calls `parse_session_basename()` to populate `subject`, `datetime`, `task`.

---

### 3b. Batch API

```python
# All in src/murineshiftwork/readers/batch.py

def load_session(session_dir: Path | str) -> MswSession:
    """Single session. Wraps read_session_data(); populates MswSession fields."""

def load_acquisition(acquisition_dir: Path | str) -> list[MswSession]:
    """All sessions inside one acquisition dir.
    Reads acquisition_manifest.yaml if present; falls back to scanning for session dirs.
    Sets acquisition_name and acquisition_dir on each MswSession."""

def load_subject(subject_dir: Path | str) -> list[MswSession]:
    """All sessions under a subject dir.
    Handles both 2-level (legacy: subject/session/) and
    3-level (current: subject/acquisition/session/) directory structures."""

def find_sessions(
    data_root: Path | str,
    subject:          str | None = None,   # fnmatch pattern, e.g. "t013*"
    task:             str | None = None,
    namespace_version: str | None = None,
    artifact_format:  str | None = None,
    from_date:        datetime | None = None,
    to_date:          datetime | None = None,
) -> list[MswSession]:
    """Walk data_root; yield MswSession for every readable session dir matching filters.
    Skips unreadable dirs with a WARNING (never raises on individual bad sessions)."""
```

**Directory depth handling:**

```
# 2-level (legacy, pre-2026-05-27)
subject_dir/
  session_basename/       ← session dir (direct child)

# 3-level (current, post-2026-05-27)
subject_dir/
  acquisition_basename/   ← acquisition dir
    session_basename/     ← session dir (grandchild)
```

`load_subject()` distinguishes these by checking whether direct children look like session dirs (contain `.msw.` files or `task_settings.py`) vs. acquisition dirs (children contain session dirs).  Uses `detect_artifact_format()` as the probe.

---

### 3c. Alignment check script

To be written after Phase 2a (fixture_legacy) and Phase 3a/3b are done.

**Intended use:** post-hoc validation of a joint OE+MSW recording — confirm that TTL barcodes recorded on an OE input channel match the MSW session's barcode log.

```python
# scripts/check_ephys_alignment.py  (or tests/test_opto_alignment_real.py)

def check_ephys_alignment(
    session_dir:    Path,
    oe_recording_dir: Path,
    ttl_channel:    int = 1,
    verbose:        bool = True,
) -> AlignmentReport:
    """Load MSW session + OE TTL events; run barcode alignment; return report.

    Returns AlignmentReport(
        n_msw_barcodes:   int,
        n_oe_barcodes:    int,
        n_matched:        int,
        match_rate:       float,          # n_matched / n_msw_barcodes
        time_offset_s:    float,          # median MSW→OE clock offset
        max_jitter_ms:    float,          # max absolute timing error
        passed:           bool,           # match_rate >= 0.95 and max_jitter_ms < 5
        issues:           list[str],
    )
    """
```

Uses `align_session_to_ephys()` from `readers/alignment.py` (already exists).  OE TTL input channel is a CLI arg (different rigs use different channels for the barcode input).

Blocked on: `fixture_legacy` (Phase 2a) + real OE session on acquisition machine.

---

### 3b-extension. Multi-protocol reader (session_manifest.yaml)

**When `session_manifest.yaml` is present in session_dir:**

```python
# inside _read_session_yaml, after scanning files dict:
manifest_path = session_dir / "session_manifest.yaml"
if manifest_path.exists():
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    subprotocols = manifest.get("subprotocols", [])
    sp_dfs = []
    for sp in subprotocols:
        sp_file = session_dir / sp["file"]
        if sp_file.exists():
            sp_df = read_trial_df(sp_file)
            if sp_df is not None:
                sp_df["subprotocol"] = sp["name"]
                sp_dfs.append(sp_df)
    if sp_dfs:
        data["df"] = pd.concat(sp_dfs, ignore_index=True)
    data["subprotocols"] = subprotocols
```

`data["is_complete_session"]`: all subprotocols `status: complete` AND df loaded.
No manifest → current single-JSONL behaviour unchanged.

---

### 3c. New fixtures needed

Current fixture coverage matrix:

| Fixture | ns_version | artifact_format | task | ephys | multi-protocol | manifest |
|---|---|---|---|---|---|---|
| fixture_pkl | LEGACY | SEPARATE_JSON | fixedsubjects | ✗ | ✗ | ✗ |
| fixture_jsonl | V1 | SEPARATE_JSON | fixedsubjects | ✗ | ✗ | ✗ |
| fixture_v2 | V1 | SESSION_YAML | fixedsubjects | ✗ | ✗ | ✗ |
| fixture_fixedsubjects | V1 | SESSION_YAML | fixedsubjects | ✗ | ✗ | ✗ |
| fixture_sequence | V1 | SESSION_YAML | sequence | ✗ | ✗ | ✗ |
| **fixture_legacy** | LEGACY | **LEGACY** | prob_switch | ✗ | ✗ | ✗ |
| **fixture_optotagging** | V1 | SESSION_YAML | optotagging | **✓** | **✓** | **✓** |

`fixture_legacy`: user copying s080–s090 session from `/ceph/sjones/users/lars/data/`.

`fixture_optotagging`: copy from `/ceph/sjones/users/lars/data/_test_subject/_test_oe_controller__20260527_132639__ephys/` — one of the complete optotagging sessions.  Sanitize hostnames/paths; keep `parent_acquisition` block and `session_manifest.yaml` intact.  Must include subprotocol JSONL files (flat or subdir).

Once added:
```python
# test_reader_session_format.py FIXTURE_EXPECTATIONS:
("fixture_legacy",     NAMESPACE_LEGACY, ARTIFACT_FORMAT_LEGACY),
("fixture_optotagging", NAMESPACE_V1,    ARTIFACT_FORMAT_SESSION_YAML),
```

```python
# test_reader_task_fixtures.py — new test class:
class TestOptotTaggingFixture:
    def test_is_ephys_session(self)           # settings.ephys populated
    def test_subprotocols_loaded(self)         # data["subprotocols"] present
    def test_df_has_subprotocol_column(self)   # "subprotocol" col in df
    def test_all_subprotocol_dfs_merged(self)  # df rows = sum of subprotocol rows
    def test_parent_acquisition_backend(self)  # settings.ephys["backend"] == "open_ephys"
```

---

### 3d. Test additions for Phase 3

When `MswSession` and batch API exist:

```python
# tests/test_reader_models.py
def test_load_session_returns_msw_session(fixture_v2_dir)
def test_load_session_populates_identity_fields(fixture_v2_dir)
def test_load_session_legacy_no_settings_process(fixture_legacy_dir)
def test_load_session_ephys_session(fixture_optotagging_dir)

# tests/test_reader_batch.py
def test_load_subject_2level_dir(tmp_path)      # symlink fixtures into subject layout
def test_load_subject_3level_dir(tmp_path)
def test_find_sessions_filter_by_task(tmp_path)
def test_find_sessions_skips_unreadable(tmp_path)
def test_load_acquisition_reads_manifest(tmp_path)
def test_load_acquisition_handles_running_status(tmp_path)
```

---

## Related plans

- `PLAN_oe_remote.md` — `msw oe` subcommand + namespace wiring
- `PLAN_session_manifests.md` — `acquisition_manifest.yaml` / `session_manifest.yaml` format (used by `load_acquisition()`)
- `IMPLEMENTATION_PLAN.md` — `msw-readers` future extraction (currently in monolith; keep clean boundary)
