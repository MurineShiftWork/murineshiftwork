# msw action

Execute a one-shot hardware action on a named device without starting a full task session.

```
msw action --setup <name> <device> <action> [key=value ...]
```

## Examples

```bash
# Open valve 1 for 50 ms
msw action --setup setup_a bpod valve_pulse valve_id=1 duration_s=0.05

# Flush valve 3 (200 pulses × 50 ms)
msw action --setup setup_a bpod valve_flush valve_id=3

# Deliver fixed volume
msw action --setup setup_a bpod valve_volume valve_id=1 volume_ul=3.0
```

## Notes

- Opens a fresh Bpod connection: do not run while a task session is active.
- Valve actions use the setup's calibration data (for `valve_volume`).
- Port is resolved from the setup YAML via `port_by_path`.
