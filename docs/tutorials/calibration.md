# Tutorial: Valve Calibration

> Skeleton — fill in.

## Overview

Bpod valve calibration maps opening time (seconds) to dispensed volume (µL) using an
exponential fit. Calibration data is stored in the setup YAML.

## Steps

1. **Run the calibration task**

```bash
msw run -s _test_subject -t _calibration_water_with_serial_scale --setup <setup_name>
```

   Follow the on-screen prompts. Weigh water dispensed at each valve opening time.

2. **View calibration plots**

```bash
msw calibration --setup <setup_name> --output-dir ./calibration_plots/
```

3. **Check the setup YAML**

   Calibration data is written to `<config_dir>/setups/<setup_name>.yaml` under
   `calibrations.bpod_valve.<valve_id>`.

## Troubleshooting

- R² < 0.95: check for air bubbles, repeat measurement
- Curve not monotone: outlier points — remove and re-run
