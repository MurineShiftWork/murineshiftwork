# Water Calibration

## Overview

Valve opening times (ms) are mapped to dispensed water volumes (µL) via an exponential fit.
Calibration data lives in `msw_configs/setups/<setup>.yaml` under `calibrations.bpod_valve`.

## Running a calibration

```bash
msw run -t _calibration_water_with_serial_scale -s _test_subject --setup setup-1
```

This records (valve_opening_time, water_weight_g, n_drops) rows and saves them to
`~/.murineshiftwork/calibration.water.<setup>.csv`.

## Migrating to setup YAML

After calibration, run:

```bash
python tools/migrate_calibrations_to_setup_yaml.py
```

Only the most-recent session's data is used (by date of `measurement_time`).

## Format

```yaml
calibrations:
  bpod_valve:
    "1":                           # valve ID (string)
      updated: "2026-04-15T14:32:00"
      points:                      # [[open_ms, volume_ul], ...]
        - [20.0, 0.823]
        - [40.0, 1.651]
        - [60.0, 2.512]
        - [80.0, 3.378]
    "3":
      updated: "2026-04-15T14:32:00"
      points:
        - [20.0, 0.771]
        - [40.0, 1.593]
```

## Validation

`ValveCalibration.validate()` checks:
- R² ≥ 0.95 for the exponential fit
- Monotonically increasing (more time → more water)
- Positive slope (b > 0)

Borderline valves (R² 0.90-0.95) still run but log a WARNING and need recalibration.

## Per-trial reward delivery

At task startup, `ValveCalibration.volume_to_open_ms(target_ul)` is called once per valve
to compute the opening time for the target reward volume.  The result is used directly in
Bpod state machine `state_timer` values.
