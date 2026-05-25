# Setup Config

Each physical setup has a YAML file at `msw_configs/setups/<setup_name>.yaml`.

## Minimal skeleton

```yaml
name: setup-1
devices:
  bpod:
    type: bpod
    port_by_path: pci-0000:00:14.0-usb-0:10.1:1.0
calibrations:
  bpod_valve: {}
```

## Full example

```yaml
name: setup-1
devices:
  bpod:
    type: bpod
    port_by_path: pci-0000:00:14.0-usb-0:10.1:1.0
  stage:
    type: stage_tower
    port_by_path: pci-0000:00:14.0-usb-0:10.4.4.3:1.0-port0
    axes:
      x: {motor_id: 11, position_min: 1, position_max: 999, velocity_max: 200, operating_mode: OP_POSITION}
      y: {motor_id: 12, position_min: 1, position_max: 999, velocity_max: 200, operating_mode: OP_POSITION}
      z: {motor_id: 13, position_min: 1, position_max: 999, velocity_max: 200, operating_mode: OP_POSITION}
    known_positions:
      reward: {x: 500, y: 200, z: 300}
  pulsepal:
    type: pulsepal
    port_by_path: pci-0000:00:14.0-usb-0:10.2:1.0
cameras:
  backend: rce
  config: /mnt/maindata/msw_configs/device_configs/cameras/setup-1.cameras.yaml
calibrations:
  bpod_valve:
    1:
      updated: "2026-04-15T14:32:00"
      points: [[20.0, 0.8], [40.0, 1.6], [60.0, 2.4], [80.0, 3.3]]
    3:
      updated: "2026-04-15T14:32:00"
      points: [[20.0, 0.7], [40.0, 1.5], [60.0, 2.3], [80.0, 3.1]]
```

## Device types

| type | required fields |
|------|-----------------|
| `bpod` | `port_by_path` |
| `pulsepal` | `port_by_path` |
| `stage_tower` | `port_by_path`, `axes` |
| `serial_generic` | `port_by_path` |

## Camera config

### RCE backend (RPi camera colony)

```yaml
cameras:
  backend: rce
  config: /mnt/maindata/msw_configs/device_configs/cameras/setup-1.cameras.yaml
```

`config` is the path to the RCE ensemble YAML. Absolute or relative to `msw_configs/`.

### FLIR + Bonsai backend

One Bonsai subprocess is launched per camera entry.  Each camera is specified
with its SDK index and (for FlyCapture) its frame rate:

```yaml
cameras:
  backend: flir_bonsai
  driver: flycap                # flycap (FlyCapture2) or spinnaker (Spinnaker SDK)
  bonsai_exe: C:\Users\lab\AppData\Local\Bonsai\Bonsai.exe
  cameras:
    - index: 0
      fps: 60
    - index: 1
      fps: 60
```

| Field | Default | Description |
|---|---|---|
| `driver` | `flycap` | `flycap` (FlyCapture2 SDK) or `spinnaker` (Spinnaker SDK) |
| `bonsai_exe` | `""` | Full path to `Bonsai.exe`. Falls back to `BONSAI_EXE` env var. |
| `workflow` | `""` | Override workflow stem. Defaults to `run-flir-{driver}-1cam`. |
| `cameras` | `[]` | List of per-camera specs. Each entry: `index` (int) + `fps` (int, default 60). |

**`index`** is the SDK enumeration index. Run `msw flir list-cameras --driver flycap`
on the acquisition machine to see which index maps to which serial number, then
set them here explicitly.  Non-consecutive indices (e.g. 0 and 2, skipping a
disconnected camera) are valid.

**`fps` (FlyCapture only)**: passed as `-p cam1fps=N` to the Bonsai workflow at
launch, which sets the `FramesPerSecond` property on the FlyCapture node.
For Spinnaker, `fps` is ignored — frame rate is configured inside the workflow
XML in the Bonsai editor.

**Finding `bonsai_exe`**: run `msw flir find-bonsai` on the acquisition machine.
The printed path goes directly into this field. Alternatively export `BONSAI_EXE`
as a system environment variable and omit the field from the YAML.

**Shorthand** (all cameras same fps, consecutive indices from 0):

```yaml
cameras:
  backend: flir_bonsai
  driver: flycap
  bonsai_exe: C:\Users\lab\AppData\Local\Bonsai\Bonsai.exe
  n_cameras: 2
  fps: 60
```

**Per-camera optical parameters** (gain, shutter, exposure) are set inside the
Bonsai workflow XML — open it in the Bonsai editor on the acquisition machine.

## Valve calibration behaviour

`msw run` injects `valve_s_for_ul` into task settings from the setup's `bpod_valve` calibration.

- **Staleness warning**: if a valve's `updated` timestamp is more than 180 days old, a warning is logged at session start. The calibration is still used — recalibrate before data collection.
- **Missing calibration (empty `bpod_valve: {}`)**: a built-in fallback is used and a loud warning printed. This is for debug runs only — never use for experiments.
- **Partial calibration (some ports missing)**: hard error at session start. If you have any valve entries, all ports used by the task must be present.

## Calibration migration

To migrate water and stage calibrations from the legacy `~/.murineshiftwork/` flat files:

```bash
python tools/migrate_calibrations_to_setup_yaml.py
```

## Finding port_by_path

```bash
udevadm info /dev/ttyACM0 | grep by-path
# or
ls -la /dev/serial/by-path/
```
