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
| `--setup <name>` | Setup name: resolves Bpod port and valve calibration from setup YAML |
| `--task-mode <name>` | Apply named config block from `task.yaml mode:` section |
| `-ts KEY=VALUE` | One-off task setting override (highest priority) |
| `-o <path>` | Output data directory (default: `~/data`) |
| `-b / --port-bpod <port>` | Bpod serial port (overrides setup YAML, default `/dev/ttyACM0`) |
| `-p / --port-pulsepal <port>` | PulsePal serial port (default `/dev/ttyACM1`) |
| `--port-stage <port>` | Stage controller serial port (default `/dev/ttyUSB0`) |
| `--port-scale <port>` | Weighing scale serial port (calibration tasks only) |
| `--simulate` | Use SimBpod: no hardware required |
| `-l / --log-level <level>` | Log level (INFO, DEBUG, WARNING, …) |
| `--debug` | Sets log level to DEBUG; if subject YAML not found, falls back to `_test_subject` |
| `--link-to <basename>` | Manually set the host acquisition folder (session saved at `<out-path>/<subject>/<basename>/<session>`) |
| `--host TYPE[:URL]` | Attach to a host acquisition system. TYPE=`openephys` reads `open_ephys_url` from machine config; append `:HOST` to override. Example: `--host openephys` or `--host openephys:10.0.10.111` |
| `-m / --meta KEY=VALUE` | Arbitrary metadata pairs (e.g. `-m project=myproject cohort=1`) |
| `--meta-experimenter <name>` | Experimenter name or initials (shorthand for `-m experimenter=NAME`) |

## Examples

```bash
# Standard session
msw run -s mouse001 -t sequence --setup setup_a

# Override reward volume for one session
msw run -s mouse001 -t sequence --setup setup_a -ts REWARD_VOLUME_UL=5.0

# Habituation mode (written to subject YAML for next time)
msw run -s mouse001 -t probabilistic_switching --task-mode habituation

# Simulate without hardware
msw run -s _test_subject -t _test_flush_valves --simulate
```

## Settings priority

See [Config System](../concepts/config_system.md) for the full 5-level priority chain.
