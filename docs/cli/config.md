# msw config

Inspect config paths and configs, and materialise new bundled keys into your config-dir overlays.

Config overlays and the deep-merge layering are explained in
[Config Overlays](../howto/config_overlays.md); this page is the command reference.

## Subcommands

### show

```bash
msw config show                        # resolved config/data paths + the machine config
msw config show <kind> <name>          # a resolved subject | setup | task config
msw config show <kind> <name> --raw    # the on-disk overlay file instead of the merged config
```

With no arguments, prints the resolved `config_dir` / `data_dir` and the main machine config
(`~/.murineshiftwork/msw_machine.yaml`). With a `<kind>` (`subject`, `setup`, or `task`) and a
`<name>`, prints that config — by default the **resolved** (schema-validated) view; `--raw` shows
the raw on-disk overlay file instead.

```bash
msw config show
msw config show task sequence
msw config show subject mouse001 --raw
```

### upgrade

```bash
msw config upgrade task <name> [--dry-run] [--yes]
msw config upgrade --all [--dry-run] [--yes]
```

Adds keys that are **new in the bundled `task.yaml`** to your config-dir task overlay, writing a
timestamped `.bak` first. Your own values are never touched — only missing keys are added, with
their bundled defaults.

You do **not** need this for new keys to take effect. At runtime the overlay deep-merges on top of
the bundled defaults, so any key you have not set is already inherited automatically (see
[Config Overlays](../howto/config_overlays.md)). `upgrade` **materialises** those new keys into your
overlay file so they are visible and version-controlled — useful after a package upgrade when a task
gains parameters you want to see or customise deliberately.

- Only `task` overlays are upgraded. `setup` and `subject` YAMLs are user-authored (no bundled
  template) and are rejected.
- `--all` upgrades every task overlay under `<config_dir>/tasks/`.
- `--dry-run` previews the keys that would be added and writes nothing.
- `--yes` applies without the interactive confirmation.

```bash
# Preview which new keys a task overlay is missing
msw config upgrade task probabilistic_switching_fixedsubjects --dry-run

  probabilistic_switching_fixedsubjects: 1 new bundled key(s):
      + default.required_devices
  would update 1 overlay(s).

# Apply (writes <overlay>.bak, then adds the keys)
msw config upgrade task probabilistic_switching_fixedsubjects --yes

# Upgrade every task overlay at once
msw config upgrade --all --yes
```

After applying, stage only the changed (tracked) overlay files in your `config_dir` repo:

```bash
git add -u tasks/          # tracked modifications only, no untracked files
git diff --cached          # review the added keys before committing
```

### migrate-subjects

```bash
msw config migrate-subjects [--dry-run]
```

Upgrades every subject config under `<config_dir>/subjects/` to the current schema: adds the
`task_state` container and seeds the sequence task's earned level from the retired `start_level`.
Writes a timestamped `.bak` per file. `--dry-run` previews without writing.

## Common options

Every subcommand accepts `-cd` / `--config-dir <path>` to target a config dir other than the one
resolved from the machine config.
