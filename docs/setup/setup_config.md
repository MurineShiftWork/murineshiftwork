# Setup Config

Each physical setup has a YAML file at `msw_configs/setups/<setup_name>.yaml`.

## Skeleton

`msw setup create <name>` generates a complete skeleton showing all fields with their
defaults.  Edit `port_by_path` and add devices as needed.

```yaml
name: my-setup
devices:
  bpod:
    type: bpod
    port_by_path: FILL_IN_PORT_BY_PATH
cameras: null
calibrations:
  bpod_valve: {}
  stale_days: 180
hooks:
  pre_task: []
  post_task: []
```

`cameras: null` means no cameras configured.  See the Camera config section below.
`stale_days` and empty hook lists are the defaults — omit them if you don't need to
override.

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
with its SDK index, a role name, and its manufacturer serial number:

```yaml
cameras:
  backend: flir_bonsai
  driver: flycap                # flycap (FlyCapture2) or spinnaker (Spinnaker SDK)
  bonsai_exe: C:\Users\lab\AppData\Local\Bonsai\Bonsai.exe
  cameras:
    - index: 0
    - index: 1
```

| Field | Default | Description |
|---|---|---|
| `driver` | `flycap` | `flycap` (FlyCapture2 SDK) or `spinnaker` (Spinnaker SDK) |
| `bonsai_exe` | `""` | Full path to `Bonsai.exe`. Falls back to `BONSAI_EXE` env var. |
| `workflow` | `""` | Override workflow stem. Defaults to `run-flir-{driver}-1cam`. |
| `cameras` | `[]` | List of per-camera specs. Each entry requires only `index`. |
| `cameras[].index` | required | SDK enumeration index. Run `msw flir list-cameras` to resolve. |

**`index`** is the SDK enumeration index used to select the physical camera.
It is not guaranteed stable across reboots; if cameras are re-enumerated
differently, update the indices here.  Serial numbers are discovered at runtime
by the Bonsai workflow — see the sidecar section below.

**Frame rate** must be configured in the SDK GUI (FlyCapture2 / Spinnaker
Viewer) and saved to camera non-volatile memory, not via this config.

**Finding `bonsai_exe`**: run `msw flir find-bonsai` on the acquisition machine.
The printed path goes directly into this field. Alternatively export `BONSAI_EXE`
as a system environment variable and omit the field from the YAML.

**Shorthand** (consecutive indices from 0):

```yaml
cameras:
  backend: flir_bonsai
  driver: flycap
  bonsai_exe: C:\Users\lab\AppData\Local\Bonsai\Bonsai.exe
  n_cameras: 2
```

**Per-camera optical parameters** (gain, shutter, exposure) are set inside the
Bonsai workflow XML — open it in the Bonsai editor on the acquisition machine.

### FLIR session metadata sidecar

At the start of each recording Python writes `{session}.flir.meta.yaml` to the
session output directory, merging per-camera meta files written by Bonsai at
startup.  The Bonsai workflows query the camera serial number via the
FlyCapture2Managed / Spinnaker .NET API and write
`{output_dir}/{session}__cam{index}__meta.yaml` before opening the capture
stream (see `docs/work_plans/PLAN_flir_bonsai_serial.md` for the workflow
change details).

Example sidecar once the Bonsai workflows are updated:

```yaml
flir_acq_format_version: 1
session: s001__20260609_143022
datetime: "2026-06-09T14:30:22"
driver: flycap
workflow: run-flir-flycap-1cam
bonsai_exe: C:\Users\lab\AppData\Local\Bonsai\Bonsai.exe
cameras:
  - cam_index: 0
    serial: "12345678"
    datetime: "2026-06-09T14:30:23"
    bonsai_session: s001__20260609_143022__cam0
  - cam_index: 1
    serial: "87654321"
    datetime: "2026-06-09T14:30:23"
    bonsai_session: s001__20260609_143022__cam1
```

`bonsai_session` is the subdirectory Bonsai creates under `output_dir` for
that camera.  Post-processing resolves `cam_index → serial` from this file.

## Open Ephys integration

Set `open_ephys_url` to the IP or hostname of the Open Ephys GUI process for this rig:

```yaml
open_ephys_url: 10.0.10.111
```

This enables `--host openephys` without passing the address on the CLI each time.
`msw run` reads the URL from the active setup config, so setups without OE simply omit the field.
Machine config (`~/.murineshiftwork/msw_machine.yaml`) is checked as a fallback for backward compatibility.

## Hooks

Pre- and post-task hooks are Python classes registered by dotted import path.
See `docs/concepts/hook_system.md` for the full API.

```yaml
hooks:
  pre_task:
    - mypackage.hooks.FetchSubjectLevel
  post_task:
    - mypackage.hooks.UploadResults
```

Empty lists (the default) mean no hooks run.

## Valve calibration behaviour

`msw run` injects `valve_s_for_ul` into task settings from the setup's `bpod_valve` calibration.

- **Staleness warning**: if a valve's `updated` timestamp is older than `stale_days` (default 180), a warning is logged at session start. The calibration is still used — recalibrate before data collection. Override per-setup with `calibrations.stale_days: 90`.
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
