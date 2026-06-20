# Session Files

## File types produced per session

| File suffix | Description |
|---|---|
| `*.msw.session.yaml` | Session metadata: format version, task, subject, process settings, task settings |
| `*.msw.df.jsonl` | Trial dataframe: one JSON object per line; first line is a version header |
| `*.msw.log` | Session-scoped text log (`INFO`-level output) |
| `*.msw.plot_spec.yaml` | Plot specification for the online monitor |
| `*.msw.csv` | Raw Bpod event log: present only in legacy sessions (pre-v2) |

For multi-subprotocol tasks (optotagging), each subprotocol writes its own JSONL:

| File | Description |
|---|---|
| `{basename}_{protocol}.msw.df.jsonl` | Per-subprotocol trial dataframe |
| `session_manifest.yaml` | Lists subprotocols, their JSONL files, barcodes, and completion status |

## `.msw.session.yaml` structure

```yaml
msw_format_version: 2
process:
  msw_version: "2.1.1"
  git_commit: "abc1234"
  session_uuid: "d4e5f6..."
  task: sequence
  subject: mouse001
  setup: setup-npx2
  serial_port: /dev/ttyACM5
  out_path: /data/data
  session_folder: /data/data/mouse001/mouse001__20260526_100149_223167__sequence
  session_basename: mouse001__20260526_100149_223167__sequence
  datetime: "20260526_100149_223167"
task_settings:
  start_level: 1
  stop_trials: 500
  ...
# present only when --host openephys was passed
host_session:
  backend: openephys
  session_name: "mouse001__20260525_074402__ephys_multi_behavior"
  subject: mouse001
  parent_directory: "/data/rig1"
  oe_session_name: "mouse001__20260525_074402__pxi"
  status: IDLE
```

`host_session` is written at session start when `--host openephys` is passed.
It captures which external session container this behavioural acquisition was
nested inside, linking back to the ephys data directory.  `session_name`
matches the second path component of `base_text` as set by `oe-remote`, which
is also the folder name passed as `linked_to` to `generate_session_paths()`.
Older session files use the key `host_acquisition` or `parent_acquisition`
(still read by the reader for backward compatibility).

## `.msw.df.jsonl` structure

First line is a version header:

```json
{"_msw_version": "1.0"}
```

Subsequent lines are one trial dict each:

```json
{"Bpod start timestamp": 0.0, "Trial start timestamp": 1.23, "trial_index": 0, "outcome": "correct", ...}
```

Read via `load_trial_data(filepath)` (returns a list of dicts, header skipped) or
`read_trial_df(filepath)` (returns a pandas DataFrame).

## `read_session_data()` return keys

`from murineshiftwork.readers.session import read_session_data`

| Key | Type | Description |
|---|---|---|
| `namespace_version` | `str \| None` | Basename datetime format: `"v1"` (microsecond precision) or `None` if unparseable |
| `artifact_format` | `str` | Storage format: `"session_yaml"`, `"separate_json"`, or `"legacy"` |
| `msw_version` | `str` | Version string from `process.msw_version`; `"legacy"` or `"< 1.0.0"` for older sessions |
| `is_legacy_session` | `bool` | True if session uses pre-`.msw.` file naming |
| `is_complete_session` | `bool` | True if all required files are present and loaded |
| `is_ephys_session` | `bool` | True if `settings.ephys` key is present |
| `df` | `DataFrame \| None` | Trial dataframe from `.msw.df.jsonl` or `.msw.df.pkl` |
| `settings.task` | `dict` | Task settings |
| `settings.process` | `dict` | Process/run settings (non-legacy sessions) |
| `settings.stage` | `dict` | Stage settings (if present in session YAML) |

`namespace_version` and `artifact_format` are derived by `detect_session_format()`
from `murineshiftwork.readers.namespace`. Call that function directly if you need
format info without loading session data.

### Artifact format constants

| Constant | Value | Description |
|---|---|---|
| `ARTIFACT_FORMAT_SESSION_YAML` | `"session_yaml"` | Single `.msw.session.yaml` (v2+, current) |
| `ARTIFACT_FORMAT_SEPARATE_JSON` | `"separate_json"` | Two separate `.msw.settings.process.json` + `.msw.settings.task.json` files |
| `ARTIFACT_FORMAT_LEGACY` | `"legacy"` | `task_settings.py` + `switching.pkl/csv` |

## Data directory layout

All sessions use a consistent 3-level layout: `subject / session / acquisition`.
The session directory is the outer container; the acquisition directory is where
`.msw.` files are written.

**Standalone** (no host, MSW auto-generates the session container):

```
<data_dir>/
└── <subject>/
    └── <subject>__<datetime>__session_<task>/   ← SESSION container (standalone)
        ├── acquisition_manifest.yaml
        └── <subject>__<datetime>__<task>/        ← ACQUISITION dir
            ├── session_manifest.yaml
            ├── <basename>.msw.session.yaml
            ├── <basename>.msw.df.jsonl
            ├── <basename>.msw.log
            └── <basename>.msw.plot_spec.yaml
```

**Host-linked** (e.g. Open Ephys via `--host openephys`; session container
name comes from the host):

```
<data_dir>/
└── <subject>/
    └── <subject>__<datetime>__ephys/            ← SESSION container (from OE)
        ├── acquisition_manifest.yaml             ← written by MSW
        ├── Record Node 101/                      ← written by Open Ephys
        └── <subject>__<datetime>__<task>/        ← ACQUISITION dir
            ├── session_manifest.yaml
            ├── <basename>.msw.session.yaml
            └── ...
```

**Optotagging** (multi-subprotocol, host-linked):

```
<data_dir>/
└── <subject>/
    └── <subject>__<datetime>__session_optotagging/  ← SESSION container
        ├── acquisition_manifest.yaml
        └── <subject>__<datetime>__optotagging/       ← ACQUISITION dir
            ├── session_manifest.yaml
            ├── <basename>.msw.session.yaml
            ├── <basename>.msw.log
            ├── <basename>__power_ramp/
            │   ├── <basename>_power_ramp.msw.df.jsonl
            │   ├── <basename>_power_ramp.msw.csv
            │   └── <basename>_power_ramp.<camera>.avi
            ├── <basename>__following_test/
            │   ├── <basename>_following_test.msw.df.jsonl
            │   └── <basename>_following_test.msw.csv
            └── <basename>__antidromic_primary/
                ├── <basename>_antidromic_primary.msw.df.jsonl
                └── <basename>_antidromic_primary.msw.csv
```

Each subprotocol gets a `{basename}__{protocol}/` subdirectory containing its
JSONL trial data, Bpod CSV event log, and any camera recordings.  The
acquisition dir holds only the shared `.msw.session.yaml`, `.msw.log`, and
`session_manifest.yaml`.

**Legacy format** (before namespace v3, depth-2, no session container):

```
<data_dir>/
└── <subject>/
    └── <subject>__<datetime>__<task>/           ← session dir at depth 2
        ├── <basename>.msw.session.yaml           # or .settings.process.json for older
        ├── <basename>.msw.df.jsonl               # or .df.pkl / switching.pkl for legacy
        └── <basename>.msw.csv                    # Bpod raw, may be absent
```

`load_subject()` detects legacy 2-level data automatically and loads it as-is.

## Sequence task: subject state fields

At session end, `save_session_end()` writes a summary to the per-subject state store
(`~/.murineshiftwork/sequence/<subject>_level.json`) and the labwatch payload:

| Field | Description |
|---|---|
| `level` | Training level at session end |
| `session_start_level` | Training level at session start |
| `total_trials` | Total `update()` calls (includes barcodes and no-response trials) |
| `task_trials` | Trials with a poke response that were scored (excludes no-response and barcodes) |
| `no_response_trials` | Trials where the animal did not initiate within `init_port_timeout_s` |
| `session_reward_count` | Number of valve openings (rewards delivered) |
| `session_liquid_ul` | Total water dispensed (µL) |

The exit log line reads: `"Session end: 'mouse001': level 12, trials 312 (289 task, 23 no-response)"`.

## Central log file

A separate per-run log is written to `~/.murineshiftwork/logs/` with the filename:

```
<setup>--<datetime>--<subject>--<task>.log
```

For example: `setup-1--2026-05-21T143201--mouse001--sequence.log`

The central log contains `DEBUG`-level output from all modules. The session log
(`<session_basename>.msw.log`) contains `INFO`-level output. Both are kept.

Up to 100 central log files are retained; older ones are pruned automatically.
Override the central log path with `--log-file <path>` (`msw run` only).
