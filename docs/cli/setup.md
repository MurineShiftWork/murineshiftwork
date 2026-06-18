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

### rename

```bash
msw setup rename <old_name> --new-name <new_name> [--force]
```

Updates the `name:` field in the YAML and renames the file. Use `--force` to
overwrite an existing target name.

## Next steps after creating a setup

See [Tutorial: Adding a Setup](../tutorials/adding_setup.md) for the full workflow:
device port paths, stage config, calibration, and optional hooks.
