# msw subject

Manage subject YAML records.

## Subcommands

### add

```bash
msw subject add -s <name> [--project <p>] [--experiment <e>] [--comment <c>] [--force]
```

Creates `<config_dir>/subjects/<name>.yaml`. Use `--force` to overwrite an existing file.

### list

```bash
msw subject list [--filter <fragment>]
```

### rename

```bash
msw subject rename -s <old_name> --new-name <new_name> [--force]
```

Updates the `name:` field in the YAML and renames the file.

### remove

```bash
msw subject remove -s <name>
```

Deletes the YAML file (no recovery).

## Subject YAML structure

See [Config System](../concepts/config_system.md) for the full YAML format and how
`task_overrides` are applied.
