# msw post

Post-acquisition data pipeline commands.

## msw post clean

Remove known noise events from `.msw.csv` session files.

```
msw post clean --data-dir <path> --event <event_name> [--dry-run]
```

| Flag | Description |
|---|---|
| `--data-dir` | Root directory to scan (recurses into subdirectories) |
| `--event` | Event string to filter out (e.g. `Port4`) |
| `--dry-run` | Report what would be removed without modifying files |

Files are backed up as `<file>.bak.<timestamp>` before modification. Files with no matching
rows are left unchanged and do not produce a backup.

### Example

```bash
# Preview what would be removed
msw post clean --data-dir ~/data/mouse001 --event Port4 --dry-run

# Apply
msw post clean --data-dir ~/data/mouse001 --event Port4
```

## msw post run

Run the full post-acquisition pipeline (rsync, h264 conversion, remote upload).

```
msw post run [options]
```

Calls `scripts/run_post_acquisition_tasks.sh`. Requires `--provision-scripts` pointing at
the `provision_rpi` scripts directory.

| Flag | Description |
|---|---|
| `--central-data` | Central data directory |
| `--local-data` | Local acquisition data directory |
| `--provision-scripts` | Path to provision_rpi scripts |
| `--rpi-group` | RPi group name |
| `--setup-group` | Setup group name |
| `--skip-upload` | Skip remote upload step |
| `--skip-rpi` | Skip RPi sync step |
| `--skip-setups` | Skip setup-machine sync step |
| `--skip-h264` | Skip h264 conversion |
| `--skip-msw-clean` | Skip the `msw post clean` noise-event cleaning step |
| `--dry-run` | Pass `--dry-run` through to the shell script |
