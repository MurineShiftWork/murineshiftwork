# Tutorial 3: Describing a rig with a setup config

## Prerequisites

[Tutorial 2: Your first session](02_first_session.md).

## What you'll learn

- What a setup YAML describes and why rigs are configured separately from tasks.
- How to create a setup and fill in its device ports.
- How `--setup` resolves hardware ports automatically so you never type a raw
  device path.

## 1. Why setups exist

A **setup** is the description of one physical rig: which devices are wired in,
on which ports, plus any rig-level metadata, calibration data, and hooks. Keeping
this in its own file is what lets the same task run on any rig. The task says
"I need a Bpod"; the setup says "on this rig, the Bpod is at this port".

A setup YAML has a few top-level sections:

- `name`: the setup's identifier (matches the file name).
- `devices`: each hardware device, its `type`, and how to reach its port.
- `calibrations` (optional): per-device calibration data, for example valve
  open-time to volume curves.
- `hooks` (optional): code to run before and after every session on this rig.

## 2. Create a setup skeleton

```bash
msw setup create rig-a
```

Expected output:

```
┌────────────────────────────────────────────────────────────┐
│ Created setup config skeleton:                              │
│ /home/you/msw_configs/setups/rig-a.yaml                     │
│ Edit the file to fill in device 'port_by_path' values       │
│ (or set 'port' for a direct /dev/ttyACM0).                  │
└────────────────────────────────────────────────────────────┘
```

This writes `setups/rig-a.yaml` containing a single `bpod` device with a
placeholder port for you to fill in.

## 3. Fill in the device port

On Linux, the most robust way to address a serial device is by its physical USB
position, which survives reboots and re-plugging. List the available paths:

```bash
ls -la /dev/serial/by-path/
```

Open `setups/rig-a.yaml` and set `port_by_path` to the symlink for your Bpod:

```yaml
name: rig-a
devices:
  bpod:
    type: bpod
    port_by_path: pci-0000:00:14.0-usb-0:2.1:1.0-port0
```

If you would rather pin a direct device path, set `port: /dev/ttyACM0` instead
of `port_by_path`. On Windows, set `port` to the COM port (for example `COM3`).

## 4. Run against the setup

Now pass `--setup rig-a`. MSW reads the setup, finds the device the task
requires, and resolves the real `/dev/tty...` path for you:

```bash
msw run -t _test_bpod_connect -s mouse001 --setup rig-a
```

MSW opens the Bpod connection on the resolved port and runs the connection test.
Because the port comes from the setup, you do not pass any device path on the
command line.

## 5. Confirm the setup is registered

```bash
msw setup list
```

Expected output:

```
┌──────────────────────────────────────────┐
│ Available setups in                       │
│ /home/you/msw_configs/setups:             │
│   - rig-a                                 │
└──────────────────────────────────────────┘
```

> The older `-b / --port-bpod` flag still exists but is deprecated. Prefer
> `--setup`, which keeps port details in one place and out of your command
> history.

## You now know

A setup YAML describes one rig's devices and ports, kept separate from task
logic so the same protocol runs anywhere. Passing `--setup <name>` resolves
hardware ports automatically, so you never type a raw device path by hand.

## Next

[Tutorial 4: Task settings and overrides](04_task_settings.md). For the full
setup file format including stage axes and calibration, see
[Adding a Setup](adding_setup.md).
