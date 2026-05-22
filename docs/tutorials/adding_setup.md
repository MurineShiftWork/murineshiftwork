# Tutorial: Adding a Setup

## 1. Initialise config directory (first time only)

```bash
msw init ~/msw_configs --data-dir ~/data
```

`config_dir` is a positional argument. `--data-dir` is optional but records the default
data output path in `~/.murineshiftwork/msw_machine.yaml`.

## 2. Create the setup skeleton

```bash
msw setup create <setup_name>
```

This writes `<config_dir>/setups/<setup_name>.yaml` with a skeleton to fill in.

## 3. Fill in device port paths

Find the by-path symlink for your serial device:

```bash
ls -la /dev/serial/by-path/
```

Edit the setup YAML and set `port_by_path` for each device.

## 4. Add stage axes (if applicable)

Under `devices.stage`, fill in `axes` (id, limits, velocity) and `known_positions`.
Run the stage configuration utility to verify positions.

## 5. Run valve calibration

See [Valve Calibration](calibration.md).

## 6. Add optional hooks

For LabWatch or other integrations, add `hooks.pre_task` / `hooks.post_task` dotted paths
to the setup YAML. See [Hook System](../concepts/hook_system.md).
