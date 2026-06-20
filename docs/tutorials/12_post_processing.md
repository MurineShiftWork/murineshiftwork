# Tutorial 12: Post-processing *(optional)*

## Prerequisites

[Tutorial 11: Hooks](11_hooks.md), and at least one session on disk.

## What you'll learn

- What the post-acquisition pipeline does and when to run it.
- The two `msw post` subcommands and their required arguments.
- How to preview a run safely before it touches anything.

## 1. What post-processing is for

Hooks run inside a session. Post-processing runs after sessions, as a separate
batch step, to move and tidy data once acquisition is done. It is the place for
work that should not slow down or risk a live session: syncing files off the rig,
converting video, and cleaning known noise out of event logs. The commands live
under `msw post`.

## 2. Clean noise events from event logs

`msw post clean` removes rows for a known noise event from `.msw.csv` event logs
under a directory tree. Always preview first with `--dry-run`:

```bash
msw post clean --data-dir ~/data/mouse001 --event Port4 --dry-run
```

This reports which files would change without modifying anything. Drop
`--dry-run` to apply:

```bash
msw post clean --data-dir ~/data/mouse001 --event Port4
```

`--data-dir` is required and is searched recursively. Each modified file is
backed up alongside the original before being changed; files with no matching
rows are left untouched.

## 3. Run the full pipeline

`msw post run` orchestrates the end-to-end pipeline: sync from rigs and cameras,
convert video, optionally clean event logs, and upload to central storage.

```bash
msw post run \
    --central-data /mnt/central/data \
    --provision-scripts /opt/provision_rpi/scripts \
    --dry-run
```

`--central-data` and `--provision-scripts` are required. Run with `--dry-run`
first; the flag is passed through to the underlying steps so you can see the full
plan before any data moves.

Individual stages can be skipped when you only need part of the pipeline:

| Flag | Skips |
|---|---|
| `--skip-rpi` | syncing from RPi cameras |
| `--skip-setups` | syncing from setup machines |
| `--skip-h264` | video conversion |
| `--skip-msw-clean` | the event-log cleaning step |
| `--skip-upload` | the remote upload step |

## 4. When to run it

Post-processing is a batch operation, typically run on a schedule (for example
overnight) or by hand at the end of a day, not after every session. Because the
clean and run commands both support `--dry-run`, you can always rehearse a run
before committing to it.

## You now know

`msw post` is the post-acquisition pipeline: `post clean` strips known noise
events from event logs, and `post run` orchestrates sync, conversion, and upload.
Both support `--dry-run`, so you can preview every change before it happens.

## Next

[Tutorial 13: Hardware abstraction](13_hardware_abstraction.md) *(optional)*. For
every flag, see the [post reference](../cli/post.md).
