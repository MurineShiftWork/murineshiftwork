# Quick Start

## Running a task

```bash
msw run -t <task_name> -s <subject_name> --setup <setup_name>
```

Example — probabilistic switching task:

```bash
msw run -t probabilistic_switching -s mouse001 --setup setup-1 \
    --meta-experimenter LBR -m experiment=GPe_cohort3
```

## Task-settings overrides

Any key defined in a task's `task.yaml` can be overridden at runtime:

```bash
msw run -t probabilistic_switching -s mouse001 --setup setup-1 \
    -ts n_max_trials=500 reward_amount_ul=2.5
```

Override priority (lowest → highest):

1. Bundled `task.yaml` defaults (shipped with the package)
2. `<config_dir>/tasks/<task_name>/task.yaml` overlay (user-managed, git-tracked)
3. Named mode (`--task-mode <name>` — picks a preset from the `mode:` section)
4. Subject YAML `task_overrides[<task_name>]`
5. CLI `-ts KEY=VALUE`

The config-dir overlay lets you keep site-specific parameter adjustments in your
`msw_configs/` repo without modifying the installed package or repeating `-ts` flags
on every run.  Create the overlay at:

```
msw_configs/tasks/<task_name>/task.yaml
```

Use the same `default:` / `mode:` structure as the bundled file.  Keys absent from the
overlay are inherited from the bundled defaults.

## Named task modes

Named modes let you switch between preconfigured parameter sets without editing any file:

```bash
# Run a habituation session (100% reward, no punishments)
msw run -t probabilistic_switching_fixedsubjects -s mouse001 --setup setup-1 \
    --task-mode stage00habituation
```

Modes are defined in `task.yaml` under the `mode:` key.  Each mode is a dict of
overrides applied on top of the `default:` section.

## Listing available tasks

```bash
msw tasks list                   # all tasks (marks [overlay] if config-dir override exists)
msw tasks list --filter opto     # filter by name fragment
msw run --help                   # also shows the task list in the epilog
```

## Serial-port resolution

When `--setup setup-1` is passed and `msw_configs/setups/setup-1.yaml` contains a
`bpod` device with `port_by_path`, MSW resolves the correct `/dev/ttyXXX` automatically.
The `-b / --port-bpod` flag is only needed on machines without a setup YAML.

## Inspecting task defaults before running

Before writing a config-dir overlay, check what parameters a task exposes:

```bash
msw tasks defaults _test_flush_valves   # print bundled task.yaml
msw tasks modes sequence                # list named mode presets
```
