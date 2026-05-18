# msw run

Start a task session.

```
msw run -s <subject> -t <task> [options]
```

## Required

| Flag | Description |
|---|---|
| `-s / --subject` | Subject name (must exist in subjects dir) |
| `-t / --task` | Task name (partial match supported) |

## Common options

| Flag | Description |
|---|---|
| `--setup <name>` | Setup name — resolves Bpod port and valve calibration from setup YAML |
| `--task-mode <name>` | Apply named config block from `task.yaml mode:` section |
| `-ts KEY=VALUE` | One-off task setting override (highest priority) |
| `-o <path>` | Output data directory (default: `~/data`) |
| `-p <port>` | Bpod serial port (overrides setup YAML) |
| `--simulate` | Use SimBpod — no hardware required |
| `--debug` | Force subject to `_test_subject`, verbose logging |

## Examples

```bash
# Standard session
msw run -s mouse001 -t sequence --setup setup_a

# Override reward volume for one session
msw run -s mouse001 -t sequence --setup setup_a -ts REWARD_VOLUME_UL=5.0

# Habituation mode (written to subject YAML for next time)
msw run -s mouse001 -t probabilistic_switching --task-mode habituation

# Simulate without hardware
msw run -s _test_subject -t _test_flush_water --simulate
```

## Settings priority

See [Config System](../concepts/config_system.md) for the full 5-level priority chain.
