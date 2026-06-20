# Tutorial 5: The config overlay chain

## Prerequisites

[Tutorial 4: Task settings and overrides](04_task_settings.md).

## What you'll learn

- The five layers MSW merges to decide a task's effective settings.
- How to create a config-dir overlay that survives package upgrades.
- Why overlays store only your deviations, not a full copy of the defaults.

## 1. The five layers

When you run a task, MSW resolves each setting by merging up to five sources, in
order from lowest to highest priority. A higher layer overrides a lower one for
any key it sets; keys it does not set fall through to the layer below.

| Order | Layer | Lives in | Scope |
|---|---|---|---|
| 1 (lowest) | bundled defaults | the task package's `task.yaml` | every rig, every animal |
| 2 | config-dir overlay | `<config_dir>/tasks/<task>/task.yaml` | this config dir (this lab/rig) |
| 3 | task mode | the `mode:` section, via `--task-mode` | per session |
| 4 | subject overrides | the subject YAML's `task_overrides` | one animal |
| 5 (highest) | CLI flags | `-ts KEY=VALUE` | one session |

The mental model: defaults are the floor, the CLI flag is the last word, and
everything in between narrows the scope from "all rigs" down to "this one run".

## 2. Create a config-dir overlay

The config-dir overlay (layer 2) is where you put settings that should apply to
every session on your machines but should not modify the installed package. The
cleanest way to start one is to copy the bundled file:

```bash
msw tasks init-configs sequence
```

Expected output:

```
Copied bundled task.yaml -> /home/you/msw_configs/tasks/sequence/task.yaml
```

Now edit `<config_dir>/tasks/sequence/task.yaml` and keep only the keys you want
to change. Everything you delete is still inherited from the bundled defaults:

```yaml
default:
  reward_amount_ul: 2.5   # this rig's standard reward volume

mode:
  probe:
    stop_trials: 50       # add or adjust a mode for this config dir
```

Confirm the overlay is detected:

```bash
msw tasks list --filter sequence
```

Expected output (note the marker):

```
Tasks:
  - sequence [overlay]
```

## 3. Why overlays are partial

An overlay deep-merges on top of the bundled defaults: it stores only your
intentional deviations, never a full copy. This is deliberate. When you upgrade
the `murineshiftwork` package and a task gains new parameters, your overlay keeps
working: the new keys arrive automatically from the updated bundled file, while
your overrides stay exactly as you set them. A full-copy config would silently
freeze you on old defaults.

Keep your `config_dir` under version control. It captures every site-specific
choice your lab has made, separately from the installed software.

## 4. Layering in practice

With the overlay above in place:

```bash
msw run -t sequence -s mouse001 --setup rig-a -ts reward_amount_ul=4.0
```

resolves `reward_amount_ul` to `4.0` (the CLI flag wins over the overlay's
`2.5`), while every key you did not touch comes from the overlay or, failing
that, the bundled defaults. Subject `task_overrides` (the next tutorial) would
slot in between the mode and the CLI flag.

## You now know

MSW resolves settings by merging five layers from bundled defaults up to CLI
flags, each narrowing the scope. A config-dir overlay stores only your
deviations, so it survives package upgrades and keeps site choices in your own
version-controlled directory.

## Next

[Tutorial 6: Managing subjects](06_subject_management.md). For the design behind
deep-merging and schema handling, see the
[Config System](../concepts/config_system.md) concept page.
