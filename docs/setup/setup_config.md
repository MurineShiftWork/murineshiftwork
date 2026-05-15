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

The `cameras.config` path can be absolute or relative to the `msw_configs/` directory.
MSW resolves it automatically when the setup is loaded.

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
