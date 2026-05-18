# Session Files

> Skeleton — fill in.

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
