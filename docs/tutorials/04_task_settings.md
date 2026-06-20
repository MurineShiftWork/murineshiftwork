# Tutorial 4: Task settings and overrides

## Prerequisites

[Tutorial 3: Describing a rig with a setup config](03_setup_config.md).

## What you'll learn

- How to see what parameters a task exposes before you run it.
- Three ways to change a task's behaviour: one-off flags, named modes, and where
  permanent changes belong.
- When to reach for each.

## 1. Inspect what a task exposes

Every task ships a `task.yaml` describing its tunable parameters and their
defaults. Read it before changing anything:

```bash
msw tasks defaults sequence
```

This prints the bundled defaults for the `sequence` task, for example:

```yaml
default:
  start_level: 1
  stop_trials: 500
  reward_amount_ul: 3.0
  show_live_plot: true
  ...
```

The task name accepts a unique substring, the same matching `msw run -t` uses.

## 2. Override a parameter for one run

To change a parameter just for the next session, pass `-ts KEY=VALUE` (one or
more, space-separated). These have the highest priority of any source:

```bash
msw run -t sequence -s mouse001 --setup rig-a \
    -ts reward_amount_ul=2.5 stop_trials=200
```

This runs the session with the reward volume and trial cap you specified,
leaving every other parameter at its default. Nothing is saved: the next run
without `-ts` uses the defaults again. Use `-ts` for quick experiments and
one-offs.

## 3. Switch to a named mode

A task can define named **modes**: preset bundles of overrides for common
situations such as habituation or expert. List a task's modes:

```bash
msw tasks modes sequence
```

Expected output (modes vary per task):

```
Modes for 'sequence':
  habituation: reward_amount_ul, stop_trials
  expert:      reward_amount_ul
  probe:       ...
```

Activate one with `--task-mode`:

```bash
msw run -t sequence -s mouse001 --setup rig-a --task-mode habituation
```

A mode is more durable than `-ts`: it is a named, reusable preset rather than a
list of keys you retype each time. Modes sit below `-ts` in priority, so you can
still override a single key on top of a mode.

## 4. Choose the right tool

| You want to... | Use | Persists? |
|---|---|---|
| try a value once | `-ts KEY=VALUE` | no |
| use a predefined preset | `--task-mode <name>` | no (but reusable) |
| change a value for one animal, every session | subject `task_overrides` | yes, per subject |
| change a value for one rig, every session | config-dir overlay | yes, per config dir |

The bottom two rows are persistent changes. They are the subject of the next two
tutorials, which cover the full settings priority chain and per-subject state.

## You now know

You can inspect a task's parameters with `msw tasks defaults`, change them for a
single run with `-ts`, and switch between preset bundles with `--task-mode`.
Permanent per-animal and per-rig changes live in config files, covered next.

## Next

[Tutorial 5: The config overlay chain](05_config_overlays.md). For the full task
list and per-task modes, see the [tasks reference](../cli/tasks.md).
