# Quick Start

## Running a task

```bash
msw run -t <task_name> -s <subject_name> --setup <setup_name>
```

Example — probabilistic switching task:

```bash
msw run -t probabilistic_switching -s mouse001 --setup setup-1 \
    --researcher LBR --experiment GPe_cohort3
```

## Task-settings overrides

Any key defined in a task's `task.settings` file can be overridden at runtime:

```bash
msw run -t probabilistic_switching -s mouse001 --setup setup-1 \
    -ts n_max_trials=500 reward_amount_ul=2.5
```

Override priority (lowest → highest):
1. `task.settings` INI defaults
2. Subject YAML `task_overrides`
3. CLI `-ts KEY=VALUE`

## Listing available tasks

```bash
msw run --help
```

## Serial-port resolution

When `--setup setup-1` is passed and `msw_configs/setups/setup-1.yaml` contains a
`bpod` device with `port_by_path`, MSW resolves the correct `/dev/ttyXXX` automatically.
The `--serial-port-bpod` flag is only needed on machines without a setup YAML.

## Sequence automated

```bash
msw run -t sequence_automated -s mouse001 --setup setup-1

# Force-start at level 3
msw run -t sequence_automated -s mouse001 --setup setup-1 -ts start_level=3 reset_level=True
```
