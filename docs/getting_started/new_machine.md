# New Machine Setup

## Prerequisites

- Python ≥ 3.10
- `pip install murineshiftwork` (or editable install from the repo)
- Access to the shared `msw_configs` directory (NFS mount or local copy)

## One-time initialisation

```bash
# Tell MSW where the shared config directory lives.
# This writes ~/.murineshiftwork/msw_machine.yaml.
msw init /mnt/maindata/msw_configs
```

After this, all `msw run` calls find configs automatically: no `--config-dir` needed.

## Config directory priority

MSW resolves the config directory in this order (first match wins):

1. `--config-dir /path` CLI argument (per-call override)
2. `MSW_CONFIG_DIR` environment variable
3. `~/.murineshiftwork/msw_machine.yaml` (written by `msw init`)
4. `/mnt/maindata/msw_configs` (historical default, used if the directory exists)

## Create a setup config

```bash
# Scaffold a new setup YAML
msw setup create setup-5

# Edit the file to fill in port_by_path values
nano /mnt/maindata/msw_configs/setups/setup-5.yaml

# List all available setups
msw setup list
```

## Register subjects

```bash
msw subject add -s mouse001
msw subject list
msw subject list -f 2025   # filter by partial name
```

## Run a test flush

```bash
msw run -t _test_flush_valves -s _test_subject --setup setup-1
# Override flush time:
msw run -t _test_flush_valves -s _test_subject --setup setup-1 -ts VALVE_OPENING_TIME_MS=80
# Use the 'wash' mode preset (30 cycles × 2000 ms):
msw run -t _test_flush_valves -s _test_subject --setup setup-1 --task-mode wash
```

## Optional: live session monitor

If a central monitor server is running, add these keys to
`~/.murineshiftwork/msw_machine.yaml` to forward live session events to it:

```yaml
log_url: http://monitor-host:8080   # ingest server base URL
log_bearer_token: <token>           # optional; omit to send without auth
```

Forwarding is best-effort and fully opt-in: with `log_url` absent the monitor
agent never starts and sessions run exactly as before. If the server is
unreachable, events are dropped silently (0.5 s timeout) and the session is
unaffected: the CLI is always the primary, fully-recorded session interface.
