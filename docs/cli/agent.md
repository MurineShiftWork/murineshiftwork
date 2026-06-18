# msw agent

Start a long-lived hardware agent that owns the Bpod connection across sessions.

```
msw agent start --setup <name> [--port <n>] [--host <addr>] [--config-dir <dir>]
```

The agent opens the Bpod once at startup and holds the connection between sessions.
Sessions are still started from the CLI (`msw run`), but can optionally be delegated
to a running agent. A WebSocket endpoint broadcasts trial events to read-only UI observers.

## Required extra

The `agent` extra must be installed before use:

```bash
pip install "murineshiftwork[agent]"
```

## Subcommands

### start

```bash
msw agent start --setup <name> [--port 8765] [--host 0.0.0.0]
```

| Flag | Description |
|---|---|
| `--setup / -S <name>` | Setup name (required): loads from `config_dir/setups/` |
| `--port <n>` | TCP port for the FastAPI server (default: `8765`) |
| `--host <addr>` | Bind host (default: `0.0.0.0`) |
| `-cd / --config-dir <dir>` | Config directory (default: from machine config) |

## Examples

```bash
# Start agent for the npx2 setup on default port
msw agent start --setup npx2

# Custom port
msw agent start --setup npx2 --port 8765

# With password auth (read by the FastAPI app at startup)
MSW_AGENT_PASSWORD=secret msw agent start --setup npx2
```

## Notes

- The agent is **phase 1**: it opens a fresh exclusive Bpod connection at startup.
  Do not run `msw run` with the same serial port while an agent is active.
- The WebSocket event bus lets read-only UI clients observe trial events without
  needing direct hardware access.
