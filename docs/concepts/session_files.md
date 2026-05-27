# Session Files

## File types produced per session

| File suffix | Description |
|---|---|
| `*.msw.session.yaml` | Session metadata — format version, task, subject, process settings, task settings |
| `*.msw.df.jsonl` | Trial dataframe — one JSON object per line; first line is a version header |
| `*.msw.log` | Session-scoped text log (`INFO`-level output) |
| `*.msw.plot_spec.yaml` | Plot specification for the online monitor |
| `*.msw.csv` | Raw Bpod event log — present only in legacy sessions (pre-v2) |

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
  out_path: /mnt/maindata/data
  session_folder: /mnt/maindata/data/mouse001/mouse001__20260526_100149_223167__sequence
  session_basename: mouse001__20260526_100149_223167__sequence
  datetime: "20260526_100149_223167"
task_settings:
  start_level: 1
  stop_trials: 500
  ...
# present only when --parent openephys was passed
parent_acquisition:
  backend: open_ephys
  acquisition_name: "mouse001__20260525_074402__ephys_multi_behavior"
  subject: mouse001
  parent_directory: "/data/rig1"
  oe_session_name: "mouse001__20260525_074402__pxi"
  status: IDLE
```

`parent_acquisition` is written at session start when `--parent openephys` is
passed. It captures exactly which Open Ephys acquisition this behavioural
session was nested inside, linking back to the ephys data directory.
`acquisition_name` matches the second path component of `base_text` as set by
`oe_remote`, which is also the folder name used as `is_child_session_to` in
`generate_session_paths()`.

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
| `raw` | `DataFrame \| None` | Bpod CSV events; only populated when `load_raw=True` and a CSV is present |

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

Current format (v2+):

```
<data_dir>/
└── <subject>/
    └── <subject>__<datetime>__<task>/
        ├── <basename>.msw.session.yaml
        ├── <basename>.msw.df.jsonl
        ├── <basename>.msw.log
        └── <basename>.msw.plot_spec.yaml
```

Legacy format (pre-v2) additionally contained:

```
        ├── <basename>.msw.csv
        └── <basename>.msw.settings.process.json   # or .msw.settings.task.json
```

## Sequence task — subject state fields

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

The exit log line reads: `"Session end — 'mouse001': level 12, trials 312 (289 task, 23 no-response)"`.

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
