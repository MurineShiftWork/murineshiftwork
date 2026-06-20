# Tutorial 6: Managing subjects

## Prerequisites

[Tutorial 5: The config overlay chain](05_config_overlays.md).

## What you'll learn

- The full lifecycle of a subject: add, list, rename, remove.
- What a subject YAML stores, including per-animal task overrides.
- How per-subject progress (like a training level) is written back automatically.

## 1. The subject lifecycle

A subject is one animal, stored as a YAML file under `<config_dir>/subjects/`.
All four management actions are subcommands of `msw subject`:

```bash
msw subject add -s mouse001 --project sleep_lhb
msw subject list
msw subject list --filter m001          # filter by name fragment
msw subject rename -s mouse001 --new-name m001_retired
msw subject remove -s mouse001          # deletes the YAML, no recovery
```

`msw subject add` writes `subjects/mouse001.yaml` and prints:

```
┌──────────────────────────────────────────────────────┐
│ Registered subject 'mouse001' at                      │
│ /home/you/msw_configs/subjects/mouse001.yaml          │
└──────────────────────────────────────────────────────┘
```

The optional `--project`, `--experiment`, and `--comment` flags are recorded as
metadata in the file.

## 2. What the subject YAML stores

Open `subjects/mouse001.yaml`. A fresh subject looks like:

```yaml
name: mouse001
registered: "2026-06-12T09:30:00"
project: sleep_lhb
experiment: ""
comment: ""
aliases: []
task_overrides: {}
```

The important field is `task_overrides`: per-animal, per-task settings that sit
at layer 4 of the [overlay chain](05_config_overlays.md). They override the rig
overlay and task defaults, but a CLI `-ts` flag still wins over them.

## 3. Set per-animal overrides

Edit the YAML to give one animal its own parameters, keyed by task name:

```yaml
task_overrides:
  sequence:
    start_level: 7          # this animal starts at level 7
    task_mode: expert       # sticky mode for this animal
  probabilistic_switching:
    reward_amount_ul: 4.0
```

Now `msw run -t sequence -s mouse001` applies these without any flags. Another
animal running the same task is unaffected: overrides are scoped to the subject
file they live in.

## 4. Sticky task modes

When you pass `--task-mode` on the command line, MSW writes the chosen mode back
into the subject's `task_overrides` as `task_mode`. The next session picks it up
automatically:

```bash
msw run -t sequence -s mouse001 --task-mode expert
# later, no flag needed:
msw run -t sequence -s mouse001     # expert mode still active
```

To clear it, remove `task_mode` from the subject YAML or pass
`--task-mode default`.

## 5. Automatic progress write-back

Some tasks track per-subject progress across sessions. The `sequence` task, for
example, advances a training level and writes the new starting level back to the
subject's state at session end. The animal resumes where it left off on the next
run, with no manual editing. This is the mechanism that lets a long training
pipeline run day after day from the same simple command.

## You now know

A subject is a YAML file you add, list, rename, and remove with `msw subject`,
and its `task_overrides` give one animal its own parameters within the overlay
chain. Sticky modes and per-subject progress are written back automatically so
the next session resumes cleanly.

## Next

[Tutorial 7: Reading session files](07_session_files.md). For the place subject
overrides occupy in the merge order, revisit
[Tutorial 5](05_config_overlays.md).
