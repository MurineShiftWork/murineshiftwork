# msw oe

Remote control of an Open Ephys GUI (v1+) over its HTTP API. Provided by the
`msw-open-ephys` plugin; install with the `oe` extra (`pip install
"murineshiftwork[oe]"`). The plugin registers an `oe` subcommand group with
`msw` and also ships a standalone `oe-remote` console script with the same
subcommands.

```
msw oe <command> [options]
```

## Subcommands

| Command | Description |
|---|---|
| `status` | Print the current GUI mode (`IDLE` / `ACQUIRE` / `RECORD`) |
| `preview` | Start acquisition without writing to disk (`ACQUIRE` mode) |
| `record` | Configure recording paths and start a recording session |
| `stop` | Stop acquisition or recording and return the GUI to `IDLE` |

## Connection options

All subcommands accept:

| Flag | Default | Description |
|---|---|---|
| `-ip / --remote-ip` | `localhost` | Open Ephys GUI host IP |
| `-port / --remote-port` | `37497` | Open Ephys HTTP API port |
| `-d / --debug` | off | Enable debug logging |

## `record`

`record` selects one of three recording modes automatically from the arguments
you pass:

- **Standalone** — no `--acquisition-extension`, no `--child`. Ephys is the only
  session.
- **Parent** — `--acquisition-extension` set. Creates a named acquisition
  container folder and records the first session inside it. The acquisition path
  is cached so later sessions can join it with `--child @last`.
- **Child** — `--child <acq_path>` or `--child @last`. Adds a session under an
  already-started acquisition container.

| Flag | Default | Description |
|---|---|---|
| `--subject` | `_test_oe_controller` | Subject identifier |
| `--session-extension` | *(required)* | Session label appended to `subject__datetime` (e.g. `pxi`, `intan_ttl`) |
| `--acquisition-extension` | `""` | Acquisition-container label (enables parent mode) |
| `--child / --is-child-session-to` | `""` | Add this session under an existing acquisition folder; pass `subject/acquisition_name` or `@last` |
| `--local-path` | `/data` | Local base data directory |
| `--remote-path` | `E:\OE_DATA\` | Remote base data directory as seen by the Open Ephys GUI |

On a successful `record`, the plugin:

1. Puts the GUI into `ACQUIRE`, configures the recording directory and base
   text, then starts `RECORD`.
2. Captures **probe metadata** live from the GUI's `/api/processors` endpoint
   (probe count, channel/stream layout) — best-effort, and never allowed to
   break the recording.
3. Writes a session metadata JSON locally and, if an `acquisition_manifest.yaml`
   already exists in the acquisition folder, stamps the probe metadata under
   `metadata.open_ephys` in that manifest.
4. Caches the acquisition path so subsequent `--child @last` sessions can attach.

## Examples

```bash
# Check what the GUI is doing
msw oe status

# Standalone recording
msw oe record --subject mouse1 --session-extension pxi

# Parent acquisition (multi-modal session container)
msw oe record --subject mouse1 \
    --acquisition-extension ephys_multi_behavior \
    --session-extension pxi

# Add a child session to the most recent acquisition
msw oe record --subject mouse1 --session-extension intan_ttl --child @last

# Stop and return to IDLE
msw oe stop
```

## See also

- [How-To: Record with Open Ephys](../howto/open_ephys.md)
- [How-To: Barcode Sync](../howto/barcode_sync.md)
- [Multi-Acquisition & Photometry](../concepts/multi_acquisition_and_photometry.md)
