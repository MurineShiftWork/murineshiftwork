# Session Files

## File types produced per session

| File | Description |
|---|---|
| `*.msw.csv` | Bpod event log — one row per event |
| `*.msw.session.yaml` | Session metadata — format version, task, subject, settings |
| `*.msw.log` | Text log for this session |

## `.msw.session.yaml` structure

```yaml
msw_format_version: 2
process:
  msw_version: "1.2.3"
  git_commit: "abc1234"
  task: sequence
  subject: mouse001
  setup: setup_a
  session_basename: mouse001_2025-08-07_001
task_settings:
  REWARD_VOLUME_UL: 3.0
  start_level: 5
  ...
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

## Data directory layout

```
<data_dir>/
└── <subject>/
    └── <date>/
        └── <session_basename>/
            ├── <session_basename>.msw.csv
            ├── <session_basename>.msw.session.yaml
            └── <session_basename>.msw.log
```

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
