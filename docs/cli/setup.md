# msw setup

Manage setup YAML records.

## Subcommands

### create

```bash
msw setup create <name> [--force]
```

Creates `<config_dir>/setups/<name>.yaml` with a skeleton to fill in.

### list

```bash
msw setup list [--filter <fragment>]
```

## Next steps after creating a setup

See [Tutorial: Adding a Setup](../tutorials/adding_setup.md) for the full workflow:
device port paths, stage config, calibration, and optional hooks.
