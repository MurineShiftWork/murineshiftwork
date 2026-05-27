# Session Namespace v2 — Design Plan

*Created 2026-05-27. Updated 2026-05-27 after analysis of real multi-session ephys acquisition:*
*`t009_acute_m1102626_206__20260526_143224__ephys_multi_behavior`*

---

## Agreed overall structure

```
subject/
  {subject}__{datetime}__{task}/          ← acquisition dir (always required)
    {acq_name}.acquisition.yaml           ← acquisition manifest (MSW-written on --child-of;
    {acq_name}.settings.ephys.json        |  OE-written independently; both may coexist)
                                          |
    {subject}__{datetime}__{task_kv}/     ← protocol dir (one per msw run nested here)
      *.msw.session.yaml                  |  full session YAML with task_settings + exit_status
      *.msw.df.jsonl                      |  trial data (protocol column for intra-run grouping)
      *.msw.log                           |
      *.msw.barcodes.jsonl                |  barcode manifest
      [substructure managed by task]      ← e.g. OE Record Node dirs, camera subdirs
                                          |
    {subject}__{datetime}__pxi/           ← external protocol dir (OE-managed, no .msw. files)
      Record Node 101/
```

**Standalone session** (no nesting): the acquisition dir IS the protocol dir. One directory,
no acquisition manifest needed. Reader falls back gracefully.

---

## Root cause analysis — example session `t009__20260526`

On the recording day, `--parent openephys` was passed but `OpenEphysParentSession.attach()`
returned `None` because `oe_remote` had not yet set `base_text` on the OE GUI (or had set
it with <2 path components). `_resolve_parent_session()` logged a WARNING and silently fell
back to standalone mode. All sessions (`probabilistic_switching_fixedsubjects`, three
`optotagging` runs) generated paths at the subject level, not inside `ephys_multi_behavior`.

Consequences on disk:
- `probabilistic_switching_fixedsubjects`: RCE camera files at subject level; MSW files
  missing (either not synced from fastdata or session crashed before `persist_settings()`)
- Three `optotagging` dirs: saved standalone at subject level; then manually copied into
  `ephys_multi_behavior/`; originals remain at subject level; `session_folder` in YAML
  points to original standalone path
- The three opto dirs appear at **both** `subject/` and `subject/acquisition/` levels;
  deduplication for DB import must use `session_uuid`

**The fix that prevents all of this**: P0 item — `--parent` failure must be a hard stop.

---

## Problem statement

Seven issues were identified. They are related but independent.

### P0 — Silent fallback when `--parent` attach fails (URGENT)

`_resolve_parent_session()` in `evaluate.py` silently falls back to standalone mode when
`OpenEphysParentSession.attach()` returns `None`. Sessions are then saved to the subject
level instead of inside the acquisition directory. The operator receives only a WARNING
log line and has no way to know until they inspect the data.

Fix: make `--parent` failure a hard `RuntimeError` unless `--force-standalone` is
explicitly passed. The ROADMAP already lists `--force-standalone` as a TODO item.

```python
# evaluate.py — _resolve_parent_session()
if info is None:
    reason = getattr(client, "fail_reason", "") or "unknown reason"
    if not args_dict.get("force_standalone"):
        raise RuntimeError(
            f"\n\n  --parent {session_type} could not attach: {reason}\n"
            f"  Sessions would be saved to the wrong location.\n"
            f"  Fix the issue, use --child-of ACQUISITION_NAME, or pass --force-standalone.\n"
        )
    logging.warning("--force-standalone: running without parent (%s)", reason)
    return
```

`--force-standalone` is added to the `msw run` parser. Without it, passing `--parent`
and having it fail is an error, not a warning. This is the single highest-impact fix
for day-to-day data hygiene.

### P1 — Non-standard artifact name in optotagging

`optotagging.py` calls `msw_file(path, "jsonl")`, producing `*.msw.jsonl`.
Every other task uses `"df.jsonl"` → `*.msw.df.jsonl`. The reader happens to
accept both but the inconsistency is invisible at write time and breaks any
tooling that expects `df.jsonl`. There is nothing to catch a wrong artifact name
when a new task is written.

### P2 — No subprotocol identity in directory names

When optotagging is run as a child of an ephys acquisition, multiple
`__optotagging` directories land as siblings. All are named identically (task =
`optotagging`, no mode). A reader or DB importer must open every session YAML to
distinguish somatic from antidromic blocks, and cannot distinguish planned
sequential blocks from retry attempts without reading the data.

### P3 — Session path mismatch in session YAML

Sessions run without `--child-of` save to a standalone path, then get synced
into the acquisition folder post-hoc. Their `session.yaml` records the original
path. The `--child-of` flag exists and works; the fix is workflow + making the
acquisition manifest explicit.

### P4 — No acquisition-level metadata file

The acquisition directory has no MSW-written file marking it as an acquisition,
listing protocols, or recording when it started. OE's `*.settings.ephys.json`
covers OE-managed acquisitions only.

### P5 — No session exit status or barcode manifest

`TaskProcess.__exit__` closes Bpod but writes nothing back to the session YAML.
No record of whether a session exited cleanly, was operator-stopped, or crashed.
Barcodes are embedded in trial records only; reconstructing sync requires loading
and parsing the full df.jsonl.

### P6 — No generic acquisition reader

`read_session_data(session_dir)` reads a single protocol dir. There is no
`read_acquisition(acq_dir)` that discovers and loads all protocol sessions nested
inside an acquisition dir. This forces callers to implement their own directory
walking, which accumulates protocol-specific logic over time.

---

## Terminology

| Term | Meaning |
|---|---|
| **acquisition** | The umbrella experimental event (one recording day / one OE acquisition). Contains one or more protocol dirs. |
| **protocol** | One `msw run` invocation. One session directory with `.msw.` files. |
| **artifact** | A file inside a protocol dir. Named `{basename}.msw.{artifact}`. |

The namespace spec level currently called `session` will be renamed `protocol` in Sprint C
(pure refactor, no filesystem change).

---

## Design decisions

### D1 — Standard artifact validation (fixes P1)

A `_STANDARD_ARTIFACTS` frozenset in `namespace/msw_files.py`. `msw_file()`
emits `logging.warning()` when called with a name not in the set. Advisory, not
a hard error.

```python
_STANDARD_ARTIFACTS = frozenset({
    "session.yaml", "df.jsonl", "df.pkl", "log",
    "plot_spec.yaml", "barcodes.jsonl",
})
```

Adding a new artifact: add it here first. CI can grep for the warning string.
The `core_artifacts` field in the namespace spec YAML documents the same list
for external tooling.

### D2 — KV extension of the protocol basename (fixes P2)

The protocol basename is extended with optional key-value pairs appended to the
task component:

```
{subject}__{datetime}__{task}[_{key}-{value}[_{key}-{value}...]]
```

Examples:
```
t009__20260526_154451__optotagging_mode-gpe_somatic
t009__20260526_155147__optotagging_mode-gpe_antidromic
mouse001__20260526_100149__sequence          # no kv — unchanged
```

**Backwards compatibility**: the existing regex `(?P<task>[\\w\\-]+)` already
matches `optotagging_mode-gpe_somatic` because `\\w` includes `_`. No regex
change required. Old sessions parse with empty kv dict.

**What goes in task_kv**: only `task_mode` when non-empty. Nothing else.
Training level and similar values belong in the session YAML, not the dirname.
The rule: only evaluate-time CLI information (known before path generation) goes
into the basename.

**Module resolution**: `generate_session_paths()` takes `task` (module name)
and `task_kv: dict = {}` separately. The basename uses both; `find_task_by_name`
uses only `task`. `process.task` in session YAML stays as the module name;
`process.task_kv` records the dict.

New utilities in `namespace/paths.py`:
```python
def parse_task_kv(task_field: str) -> tuple[str, dict[str, str]]:
    """'optotagging_mode-gpe_somatic' → ('optotagging', {'mode': 'gpe_somatic'})"""

def build_task_field(base_task: str, kv: dict[str, str]) -> str:
    """Inverse of parse_task_kv."""
```

The `_` + `-` convention is compatible with NeuroBluePrint/BIDS key-value
encoding for future cross-tool interoperability.

### D3 — Acquisition manifest (fixes P3 and P4)

When `--child-of` or `--parent` is used, MSW writes/updates
`{acquisition_name}.acquisition.yaml` at the acquisition directory level.

```yaml
# {acq_name}.acquisition.yaml
acquisition_name: t009__20260526_143224__ephys_multi_behavior
subject: t009_acute_m1102626_206
datetime: "20260526_143224"
started_at: "2026-05-26T14:32:24"
protocols:
  - basename: t009__20260526_143224__pxi
    type: external          # OE-managed; no .msw. files
  - basename: t009__20260526_154451__optotagging_mode-gpe_antidromic
    type: msw
  - basename: t009__20260526_155147__optotagging_mode-gpe_somatic
    type: msw
```

**Write point**: `_resolve_parent_session()` in `evaluate.py` after
`is_child_session_to` is confirmed. Read-modify-write with suppress on error.

**OE coexistence**: OE already writes `{acq_name}.settings.ephys.json` at the
acquisition level. Both files coexist. The MSW acquisition YAML references the
OE file via the `external` protocol entry. Readers can load both independently.

**Standalone acquisitions**: no acquisition manifest is written. The protocol
dir IS the acquisition. The reader detects this (no `.acquisition.yaml` found,
no subdirectories containing `.msw.` files).

**Not load-bearing**: sessions remain fully readable if the manifest is lost.
The manifest is an index for fast discovery; it is not required for loading
individual protocol sessions.

### D4 — Optotagging: one `msw run` per mode block (fixes P2 operationally)

Each major block (somatic, antidromic) is a separate `msw run` invocation with
`--child-of`. Within a block, the task loops over stimulation conditions; each
condition is tagged with `info.protocol` in the df.jsonl (already implemented).
The `_protocol_sequence` advisory key in task.yaml documents the intended order.

**Why not one invocation writing multiple dirs**: the task would have to manage
its own session paths and write protocol-level session YAMLs, duplicating
`TaskProcess` logic. Exit status, logging, and hooks would sit at the wrong
level.

**Intra-run protocol completeness**: `task_settings` is already in the session
YAML (written at task start — see D5). It contains `n_trials` per stimulation
condition. Completeness = compare `task_settings.stimulation.{proto}.n_trials`
against actual trial count from df.jsonl. No separate `trial_count` or
`protocols_run` manifest is needed — the task config plus the data are
sufficient and self-consistent.

**task.yaml change**:
```yaml
mode:
  gpe_somatic:
    stimulation:
      power_ramp_2mw:  { n_trials: 200, laser_power: 0.002, ... }
      power_ramp_5mw:  { n_trials: 200, laser_power: 0.005, ... }
      following_40hz:  { n_trials: 200, pulse_frequency: 40, ... }
  gpe_antidromic:
    stimulation:
      antidromic_5ms_20hz:  { n_trials: 3600, ... }
      antidromic_3ms_20hz:  { n_trials: 2400, ... }
  _protocol_sequence:   # advisory only; not a runnable mode
    - gpe_somatic
    - gpe_antidromic
```

### D5 — Exit status + task_settings in session YAML (fixes P5 partially)

**Exit status**: `TaskProcess.__exit__` writes `exit_status` into the `process:`
section before closing Bpod. A `_stopped_by_operator: bool = False` flag is set
by `stop_task()` to distinguish explicit operator stop from natural task end.

```
exit_status values:
  "complete"        — task loop exited naturally
  "operator_stop"   — stop_task() called while running
  "hardware_error"  — OSError (Bpod serial disconnect)
  "crash"           — unhandled exception
```

Wrapped in `contextlib.suppress(Exception)` so it does not mask the original
exception. Runs before `exit_safely()`.

**task_settings in session YAML**: every task that has meaningful per-protocol
config should call `update_session_yaml(task_settings=patched)` at task start.
Currently missing from optotagging. This makes expected trial counts and stim
params available without reading the original task config files. The session is
fully self-describing.

**Reader update**: `read_session_data()` exposes `exit_status` at top level,
defaulting to `"unknown"` when absent (legacy sessions).

### D6 — Barcode manifest file (fixes P5)

A dedicated `*.msw.barcodes.jsonl` is written alongside `df.jsonl`. One line per
barcode event, appended when the barcode value and wall time are captured (before
the Bpod state machine runs). Schema:

```json
{"value": 42, "wall_time": 1717000000.123, "trial_index": 0, "role": "session_start"}
{"value": 43, "wall_time": 1717000120.456, "trial_index": 1, "role": "protocol_start", "protocol": "power_ramp_2mw"}
{"value": 44, "wall_time": 1717000180.789, "trial_index": 201, "role": "protocol_end", "protocol": "power_ramp_2mw"}
{"value": 45, "wall_time": 1717000181.001, "trial_index": 202, "role": "trial"}
```

`role` values: `session_start`, `session_end`, `protocol_start`, `protocol_end`,
`trial`.

A `BarcodeLogger` helper is owned by `TaskRunner`, written to via
`self.barcode_logger.log(value, wall_time, role=..., protocol=...)` at each
`prepare_barcode()` call.

### D7 — Generic acquisition reader (fixes P6)

A new `read_acquisition(acq_dir)` function in `readers/` discovers and loads all
MSW protocol sessions nested inside an acquisition directory. It is generic —
no protocol-specific logic.

**Full design in the section below.**

---

## D7 — Acquisition reader design (detailed)

### The question

Given the example acquisition directory containing three optotagging protocol
dirs and a PXI dir, how does a reader load all protocol sessions without knowing
anything about optotagging, PXI, or the specific task modes used?

```
ephys_multi_behavior/
  *.settings.ephys.json              ← OE manifest (existing)
  *.acquisition.yaml                 ← MSW manifest (new, may be absent)
  t009__20260526_154451__optotagging/  ← MSW protocol dir
    *.msw.session.yaml
    *.msw.jsonl
    *.msw.log
  t009__20260526_155042__optotagging/  ← MSW protocol dir
  t009__20260526_155147__optotagging/  ← MSW protocol dir
  t009__20260526_143224__pxi/          ← OE protocol dir (no .msw. files)
    Record Node 101/
```

### Protocol dir discriminator

A subdirectory of an acquisition is an MSW protocol dir if and only if:

1. Its name parses as a valid MSW session basename (`parse_session_basename()`
   succeeds), AND
2. It contains at least one file matching `*.msw.*`

Condition 1 excludes generic subdirs like `Record Node 101/`.
Condition 2 excludes OE dirs like `__pxi/` whose name parses correctly but
which contain only OE binary data (no `.msw.` files).

Both checks already exist: `parse_session_basename()` in `namespace/paths.py`,
and `any(".msw." in f.name for f in d.iterdir())` is trivial. No new parsing
logic is needed.

### Discovery order (manifest first, scan as fallback)

```python
def _find_protocol_dirs(acq_dir: Path) -> list[Path]:
    """Return MSW protocol dirs inside acq_dir, manifest-first with scan fallback."""
    manifest = _load_acquisition_manifest(acq_dir)
    if manifest:
        msw_entries = [e for e in manifest.get("protocols", [])
                       if e.get("type") == "msw"]
        dirs = [acq_dir / e["basename"] for e in msw_entries]
        return [d for d in dirs if d.is_dir()]   # skip any missing

    # Fallback: scan all subdirs
    return [
        d for d in sorted(acq_dir.iterdir())
        if d.is_dir()
        and _is_msw_protocol_dir(d)
    ]
```

When the manifest is present it is authoritative (preserves run order, includes
only intended protocols). The scan fallback sorts by name (which sorts by
datetime, giving chronological order).

### `read_acquisition()` function

```python
def read_acquisition(acq_dir: Path) -> dict:
    """Load all MSW protocol sessions within an acquisition directory.

    Returns:
        acquisition_name (str)
        manifest (dict | None)   — raw acquisition YAML if present
        protocols (dict)         — {basename: read_session_data(proto_dir)}
        external_dirs (list)     — subdirs with valid basenames but no .msw. files
        unrecognised_dirs (list) — subdirs that don't match either pattern
    """
```

Each entry in `protocols` is the output of the existing `read_session_data()`.
The function adds no new session-reading logic — it is a coordinator that
discovers dirs and delegates.

### Standalone session behaviour

When `read_acquisition()` is called on a standalone session dir (no
subdirectories with `.msw.` files), `_find_protocol_dirs()` returns an empty
list and the fallback returns the dir itself as the single protocol. The function
returns a single-protocol acquisition, indistinguishable in structure from a
multi-protocol one. Callers iterate `protocols` uniformly.

### What the reader does NOT do

- It does not interpret `info.protocol` columns in df.jsonl (optotagging-specific)
- It does not know the difference between somatic and antidromic blocks
- It does not validate trial counts against task config
- It does not parse OE binary data

All of the above belong in task-specific analysis code above the reader layer.

---

## Backwards compatibility matrix

| Change | Filesystem impact | Code impact | Legacy data |
|---|---|---|---|
| `session` → `protocol` in spec | None | `build_path` callers | Not affected |
| KV pairs in basename | New dirs only | `generate_session_paths(task_kv=)` | Empty kv dict on parse |
| Acquisition manifest | New file when `--child-of` used | `_resolve_parent_session()` | Absent → scan fallback |
| `exit_status` in session YAML | None | `TaskProcess.__exit__()` | Missing key → `"unknown"` |
| `task_settings` in opto session YAML | None | optotagging writes it at start | Absent → no config in YAML |
| `"jsonl"` → `"df.jsonl"` in optotagging | New artifact name | One-line change | Old `.msw.jsonl` still loads |
| `_STANDARD_ARTIFACTS` warning | None | `msw_file()` | No effect on existing data |
| `barcodes.jsonl` | New file | `BarcodeLogger` in `TaskRunner` | Absent → alignment uses df.jsonl |
| `read_acquisition()` | None | New function in `readers/` | Works on legacy dirs via scan fallback |

---

## NeuroBluePrint alignment note

NeuroBluePrint uses generic data-stream categories (`ephys/`, `behavior/`) as
subdirectories under a session. MSW uses specific named protocol directories
(`subject__datetime__optotagging_mode-gpe_somatic`). MSW's approach is more
specific and useful for automated processing: the directory name uniquely
identifies task, mode, and timestamp without opening any file. Category mapping
(optotagging → opto stream) belongs in the task registry, not the filesystem.
The KV pair convention is deliberately compatible with NeuroBluePrint encoding.

---

## Sprint plan

### Sprint A — Immediate fixes (no architecture change)

```
[ ] P0: --force-standalone flag in parser; RuntimeError in _resolve_parent_session() when --parent fails without it
[ ] P1 fix: "jsonl" → "df.jsonl" in optotagging.py (1 line)
[ ] D1: _STANDARD_ARTIFACTS frozenset + msw_file() warning
[ ] D5: exit_status in TaskProcess.__exit__() + _stopped_by_operator flag
[ ] D5: update_session_yaml(task_settings=patched) at optotagging task start
[ ] D5: reader exposes exit_status at top level (default "unknown")
[ ] D6: BarcodeLogger class; TaskRunner.barcode_logger
[ ] D6: optotagging.py uses barcode_logger at each prepare_barcode() call
[ ] D6: sequence + other barcode tasks: add barcode_logger calls
[ ] Tests: barcodes.jsonl written and parseable; exit_status in YAML
[ ] Pre-commit + all tests green
```

### Sprint B — Namespace + acquisition structure

```
[ ] D2: generate_session_paths(task_kv=) + parse_task_kv() + build_task_field()
[ ] D2: evaluate.py wires task_mode into task_kv when non-empty
[ ] D2: process.task_kv written to session YAML
[ ] D3: acquisition YAML written/updated in _resolve_parent_session()
[ ] D3: protocol basename appended to protocols list at session start
[ ] D4: optotagging task.yaml — gpe_somatic / gpe_antidromic modes + _protocol_sequence
[ ] D7: _is_msw_protocol_dir() helper in readers/namespace.py
[ ] D7: _find_protocol_dirs() with manifest + scan fallback
[ ] D7: read_acquisition(acq_dir) in readers/acquisition.py
[ ] Tests: KV round-trip; acquisition YAML; opto modes; read_acquisition on example
[ ] Docs: session_files.md, OPTOTAGGING_SESSION_DESIGN.md
[ ] Pre-commit + all tests green
```

### Sprint C — Level rename (pure refactor, deferred)

```
[ ] namespace.msw.yaml: "session" → "protocol"
[ ] All build_path("session") callers updated
[ ] file level template updated
[ ] Tests + docs updated
```

---

## Open questions

**Q1** — Acquisition manifest append race: two protocols starting simultaneously
is unlikely (sequential by design) but possible. A suppress-on-error retry is
sufficient for now.

**Q2** — `msw sequence` command: reads `_protocol_sequence` and runs each mode
in order with `--child-of`. Deferred; wrapper script is sufficient for now.

**Q3** — DB import schema: what the importer reads from session YAML and how it
maps to the database. Out of scope here; importer should target the v2 session
format described in this document.

**Q4** — Training level: in `task_settings.start_level` in the session YAML
(already there for sequence). Does not belong in the basename.

**Q5** — `read_acquisition()` return type for standalone sessions: caller
iterates `protocols` uniformly whether there is one or many. The single-protocol
case is transparent to callers.
