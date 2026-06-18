# msw init

Initialise MSW on a new machine by writing `~/.murineshiftwork/msw_machine.yaml`.

```
msw init <config_dir> [--data-dir <path>] [--force]
```

## Arguments

| Argument | Description |
|---|---|
| `config_dir` | Path to the shared `msw_configs/` directory (created if absent) |
| `--data-dir <path>` | Default output directory for session data (written to machine config) |
| `--force` | Overwrite an existing machine config |

## Examples

```bash
# Basic init pointing at a network configs directory
msw init /mnt/maindata/msw_configs

# With explicit data dir
msw init /mnt/maindata/msw_configs --data-dir /mnt/maindata/data

# Overwrite existing machine config
msw init /mnt/maindata/msw_configs --force
```

## Notes

- `msw init` only needs to be run once per machine.
- The machine config is stored at `~/.murineshiftwork/msw_machine.yaml`.
- `config_dir` is typically a shared network path or a git-backed directory
  (`msw_configs/`) containing `setups/`, `subjects/`, and `tasks/` subdirectories.
- After init, verify with `msw setup list` to confirm the config directory is found.
