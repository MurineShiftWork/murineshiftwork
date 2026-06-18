# Tutorial: Adding a Subject

## Register a new subject

```bash
msw subject add -s mouse001 --project sleep_lhb
```

This writes `<config_dir>/subjects/mouse001.yaml`.

## Task overrides

Edit the subject YAML to set per-task parameters:

```yaml
task_overrides:
  sequence:
    start_level: 3          # override starting level
    task_mode: habituation  # sticky task mode
  probabilistic_switching:
    REWARD_VOLUME_UL: 4.0
```

### Sticky task mode

Use `--task-mode <name>` once and it's written to the subject YAML automatically.
Next session picks up the same mode without the CLI flag:

```bash
msw run -s mouse001 -t sequence --task-mode expert
# Next session:
msw run -s mouse001 -t sequence   # expert mode still active
```

To clear: remove `task_mode` from the subject YAML, or pass `--task-mode default`.

## Level progression (sequence task)

The sequence task writes `start_level` back to the subject YAML at session end.
No manual editing needed: the animal picks up where it left off.

## Other commands

```bash
msw subject list               # list all subjects
msw subject list --filter m001 # filter by name fragment
msw subject rename -s mouse001 --new-name m001_retired
msw subject remove -s mouse001
```
