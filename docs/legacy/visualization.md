# Calibration Visualization

## Plot valve calibration for all setups

```python
from murineshiftwork.logic.calibration import plot_setup_valve_calibrations

# All setups in the default config directory
plot_setup_valve_calibrations()

# Single setup
plot_setup_valve_calibrations(setup_name="setup-1")

# Save PNGs alongside setup YAMLs
plot_setup_valve_calibrations(save_fig=True, show=False)
```

Each panel shows the measured (open_time_ms, volume_µL) points and the fitted
exponential curve `a·exp(b·ms) + c` for each valve.

## CLI shortcut

```bash
python -c "from murineshiftwork.logic.calibration import plot_setup_valve_calibrations; plot_setup_valve_calibrations()"
```

## Interpreting the plot

- **Points** = individual calibration measurements
- **Curve** = exponential fit; used by `ValveCalibration.volume_to_open_ms()` at runtime
- **R² ≥ 0.95** required for a valve to pass validation; borderline valves need recalibration

## Updating calibrations

Run the migration tool after collecting new water calibration CSVs:

```bash
python tools/migrate_calibrations_to_setup_yaml.py
```

This reads `~/.murineshiftwork/calibration.water.<setup>.csv` and writes the most-recent
session's points into `msw_configs/setups/<setup>.yaml`.
