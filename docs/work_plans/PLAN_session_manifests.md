# Session and Acquisition Manifest Design

*Created 2026-05-27. Covers: manifest writer module, opto per-subprotocol Bpod split.*

---

## Why

The mandatory acquisition level (commit `449a36a`) gives sessions a predictable
`subject/acquisition/session/files` structure. Two things were missing:

1. **Discovery**: without a manifest, finding all sessions inside an acquisition requires
   scanning directories and guessing which are sessions vs. protocol subdirs.
2. **Completeness**: the opto task writes all protocols to one JSONL file, so there is no
   way to tell at a glance which protocols completed or whether the session was cut short.

Both are solved by progressive YAML manifests and per-protocol JSONL files.

---

## Directory layout

### Simple session (sequence, fixedsubjects, airpuff, ...)

```
basepath/
  mouse_01/
    mouse_01__20260527_143022_123456__session_sequence/   ← acquisition dir
      acquisition_manifest.yaml
      mouse_01__20260527_143022_123456__sequence/         ← session dir
        session_manifest.yaml
        mouse_01__20260527_143022_123456__sequence.msw.session.yaml
        mouse_01__20260527_143022_123456__sequence.msw.df.jsonl
        mouse_01__20260527_143022_123456__sequence.msw.log
        mouse_01__20260527_143022_123456__sequence.msw.plot_spec.yaml
```

### Opto session (multi-subprotocol)

```
basepath/
  mouse_01/
    mouse_01__20260527_143022_123456__session_optotagging/  ← acquisition dir
      acquisition_manifest.yaml
      mouse_01__20260527_143022_123456__optotagging/        ← session dir
        session_manifest.yaml
        mouse_01__20260527_143022_123456__optotagging.msw.session.yaml
        mouse_01__20260527_143022_123456__optotagging.msw.log
        mouse_01__20260527_143022_123456__optotagging_power_ramp.msw.df.jsonl
        mouse_01__20260527_143022_123456__optotagging_following_test.msw.df.jsonl
        mouse_01__20260527_143022_123456__optotagging_antidromic_primary.msw.df.jsonl
        mouse_01__20260527_143022_123456__optotagging_antidromic_crosscheck.msw.df.jsonl
```

### OE + behaviour session (acquisition from Open Ephys)

```
basepath/
  mouse_01/
    mouse_01__20260527_143022_123456__ephys/               ← acquisition dir (OE name)
      acquisition_manifest.yaml                            ← written by MSW at session start
      Record Node 101/                                     ← written by Open Ephys
      mouse_01__20260527_143022_123456__sequence/          ← MSW session dir
        session_manifest.yaml
        mouse_01__20260527_143022_123456__sequence.msw.session.yaml
        ...
```

---

## Manifest schemas

### acquisition_manifest.yaml

Written when `TaskProcess` creates the acquisition dir (currently happens inside
`generate_session_paths()` when it calls `Path(session_folder).mkdir()`).

```yaml
msw_manifest_version: 1
type: acquisition
acquisition_name: mouse_01__20260527_143022_123456__session_optotagging
sessions:
  - basename: mouse_01__20260527_143022_123456__optotagging
    started_at: "2026-05-27T14:30:22+00:00"
    ended_at: "2026-05-27T15:02:18+00:00"   # filled on TaskProcess exit
    status: complete                          # running | complete | aborted
```

Only one session per acquisition in the standard case. Multiple sessions would appear
if the same acquisition dir hosts an ephys + behaviour session pair from an external
parent (OE), or if a crash-recovery re-run writes a new session into the same dir.

### session_manifest.yaml

Written at session start; `subprotocols` is empty for simple sessions.

```yaml
msw_manifest_version: 1
type: session
session_basename: mouse_01__20260527_143022_123456__optotagging
subprotocols:
  - name: power_ramp
    file: mouse_01__20260527_143022_123456__optotagging_power_ramp.msw.df.jsonl
    barcode_start: 42
    barcode_end: 43
    status: complete      # running | complete | aborted
  - name: following_test
    file: mouse_01__20260527_143022_123456__optotagging_following_test.msw.df.jsonl
    barcode_start: 44
    barcode_end: 45
    status: complete
```

---

## Implementation: `namespace/manifest.py`

```python
def init_acquisition_manifest(acquisition_folder, acquisition_name) -> None:
    """Write acquisition_manifest.yaml if absent. Called once at dir creation."""

def append_session_to_acquisition(acquisition_folder, session_basename, started_at) -> None:
    """Add a session entry with status=running. Called at TaskProcess init."""

def finalize_session_in_acquisition(acquisition_folder, session_basename, status, ended_at) -> None:
    """Set status and ended_at. Called at TaskProcess exit."""

def init_session_manifest(session_folder, session_basename) -> None:
    """Write session_manifest.yaml with empty subprotocols. Called at session start."""

def append_subprotocol(session_folder, name, filename, barcode_start) -> None:
    """Add subprotocol entry with status=running. Called before each protocol."""

def finalize_subprotocol(session_folder, name, barcode_end, status) -> None:
    """Set barcode_end and status. Called after each protocol."""
```

All functions read-modify-write atomically (write to `.tmp`, rename).

---

## Implementation: call sites

| Function | Called from |
|---|---|
| `init_acquisition_manifest` | `task_process.py` `__init__` after `mkdir` |
| `append_session_to_acquisition` | `task_process.py` `__init__` after manifest init |
| `finalize_session_in_acquisition` | `task_process.py` `__exit__` |
| `init_session_manifest` | `task_process.py` `__init__` (always) |
| `append_subprotocol` | `optotagging.py` before each protocol loop |
| `finalize_subprotocol` | `optotagging.py` in `finally` block of each protocol |

---

## Opto per-subprotocol Bpod session split

Currently: one Bpod session (open → all protocols → close), one JSONL file.

Target: one Bpod close+reopen between protocols; one JSONL per protocol.

### JSONL filename convention

```
{session_basename}_{protocol_name}.msw.df.jsonl
```

Built with:
```python
proto_file = msw_file(
    str(Path(session_file_path).parent / f"{session_basename}_{protocol_name}"),
    "df.jsonl"
)
```

This keeps the file inside the session dir with a deterministic name.

### Bpod close/reopen

`TaskRunner` holds `self.bpod`. Between protocols in `Task.run()`:

```python
# end of protocol N
self.bpod.close_safely()
# beginning of protocol N+1
from murineshiftwork.hardware.bpod import BpodFactory
serial_port = self.input_kwargs.get("serial_port_bpod", "")
workspace = self.input_kwargs["session_paths"]["session_folder"]
session_name = f"{session_basename}_{protocol_name}.msw"
self.bpod = BpodFactory(serial_port=serial_port, workspace_path=workspace, session_name=session_name)
self.bpod.open()
```

This adds ~2–3 s per protocol (USB re-enumeration). Acceptable for opto (protocol gaps are
already 5–10 s for video warmup).

### Completeness check

A protocol is complete if its JSONL file exists and contains at least two rows (start + end barcode).
The session manifest `subprotocols[].status` field makes this queryable without scanning files.

---

## Reader impact

`read_session_data(session_dir)` does not change — it still reads from a session dir.

What the reader gains access to:
- `session_manifest.yaml` → can enumerate expected subprotocol files
- Per-protocol JSONL files → each loadable independently via `read_trial_df()`

A future `read_opto_session(session_dir)` returns a dict keyed by protocol name, each value
being the per-protocol trial dataframe plus barcode timestamps. This is a thin wrapper over
the session manifest + `read_trial_df()` calls.

---

## Related

- `PLAN_retrograde_reader.md` — detection layer + Phase 2b dispatch refactor
- `docs/work_plans/ROADMAP.md` — sprint items 6, 7, 8
- `OPTOTAGGING_SESSION_DESIGN.md` — protocol timing and design parameters
