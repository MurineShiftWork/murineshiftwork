# Tutorial: Valve Calibration

Bpod valve calibration maps opening time (seconds) to dispensed volume (µL) using an
exponential fit. Calibration data is stored per-setup in the config-dir YAML.

## Prerequisites

Install the calibration optional dependencies (includes both scale drivers):

```bash
pip install "murineshiftwork[calibration]"
```

This pulls in `serial-scale-hx711` (Arduino+HX711 custom scale) and
`serial-scale-bench` (RS-232/USB commercial bench scales).

Find the serial path for the scale:

```bash
ls -la /dev/serial/by-path/   # identify by physical USB port position
# or
ls /dev/ttyACM*
```

See `docs/setup/SERIAL.md` for per-setup port assignments.

## Running calibration

```bash
msw run -s _test_subject -t _calibration_liquid_dynamic --setup <setup_name> \
    --scale-port /dev/ttyACM1
```

Follow on-screen prompts: the task opens each valve for a range of durations,
the scale reports the dispensed weight, and the fit is written back to the setup YAML.

### Static (manual weight entry) variant

```bash
msw run -s _test_subject -t _calibration_liquid_static --setup <setup_name>
```

Enter weights manually when prompted (useful without a connected scale).

## Viewing calibration curves

```bash
msw calibration --setup <setup_name> --output-dir ./calibration_plots/
```

Plots are saved as PNG; R² and fit parameters are printed to stdout.

## Setup YAML location

Calibration data is written to `<config_dir>/setups/<setup_name>.yaml` under
`calibrations.bpod_valve.<valve_id>`:

```yaml
calibrations:
  bpod_valve:
    1:
      fit: exponential
      a: 0.123
      b: 4.56
      r2: 0.998
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| R² < 0.95 | Air bubbles / inconsistent dispensing | Flush, repeat |
| Scale not found | Wrong serial port | Check `SERIAL.md`, try `ls /dev/ttyACM*` |
| Curve not monotone | Outlier point | Remove that point from YAML, re-run |
| `ImportError: serial_scale_hx711` | Calibration deps not installed | `pip install "murineshiftwork[calibration]"` |
