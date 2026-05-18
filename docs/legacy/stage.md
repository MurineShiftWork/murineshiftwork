# Stage Calibration

## Overview

Stage tower axes and known positions are stored in the setup YAML under `devices.stage`.

## Format

```yaml
devices:
  stage:
    type: stage_tower
    port_by_path: pci-0000:00:14.0-usb-0:10.4.4.3:1.0-port0
    axes:
      x:
        motor_id: 11
        position_min: 1
        position_max: 999
        velocity_max: 200
        operating_mode: OP_POSITION
      y: {motor_id: 12, position_min: 1, position_max: 999, velocity_max: 200, operating_mode: OP_POSITION}
      z: {motor_id: 13, position_min: 1, position_max: 999, velocity_max: 200, operating_mode: OP_POSITION}
    known_positions:
      reward:   {x: 500, y: 200, z: 300}
      cleaning: {x: 100, y: 800, z: 300}
```

## Motor IDs per setup

| Setup  | Stage | x  | y  | z  |
|--------|-------|----|----|----|
| 1      | 1     | 11 | 12 | 13 |
| 2      | 2     | 41 | 42 | 43 |
| 3      | 3     | 71 | 72 | 73 |
| 4      | 4     | 51 | 52 | 53 |
| npx-HF | 7     | 31 | 32 | 33 |

## Migration from legacy YAML

```bash
python tools/migrate_calibrations_to_setup_yaml.py
```

This reads `~/.murineshiftwork/calibration.stage.<setup>.yaml` and merges axes/known_positions
into the setup YAML.
