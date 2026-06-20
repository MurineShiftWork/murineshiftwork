# Tutorial 14: Valve calibration *(optional)*

## Prerequisites

[Tutorial 13: Hardware abstraction](13_hardware_abstraction.md), a configured
[setup](03_setup_config.md), and the `calibration` extra installed.

## What you'll learn

- What valve calibration produces and why it lives in the setup file.
- How to run a calibration session and view the resulting curves.
- When to recalibrate.

## 1. What calibration is for

A reward valve dispenses a volume of liquid that depends on how long it is held
open. Calibration measures that relationship for each valve so the task can
request a target volume in microlitres and MSW translates it to an open time.
Calibration data is stored per rig, under `calibrations.bpod_valve` in the setup
YAML, because it is a property of that physical valve and tubing.

Install the calibration drivers first:

```bash
pip install "murineshiftwork[calibration]"
```

## 2. Run a calibration session

Calibration is a built-in task, so you run it with `msw run` like any other. The
dynamic variant drives each valve across a range of open times while a connected
serial scale reports the dispensed weight:

```bash
msw run -t _calibration_liquid_dynamic -s _test_subject --setup rig-a \
    --port-scale /dev/ttyACM1
```

Follow the on-screen prompts. The fit is written back into the setup YAML as a
list of `[open_time_ms, volume_ul]` points under the valve's entry.

If you have no scale connected, use the static variant and enter weights manually
when prompted:

```bash
msw run -t _calibration_liquid_static -s _test_subject --setup rig-a
```

## 3. View the calibration curves

`msw calibration plot` reads the points stored in your setup YAMLs and saves the
fitted curves as PDF:

```bash
msw calibration plot --setup rig-a --out ./calibration_plots/
```

Expected output:

```
Saved: ./calibration_plots/rig-a.calibration.<timestamp>.pdf
```

Omit `--setup` to plot every setup in the config directory. `plot` is the only
action of the `calibration` command: it reads and visualises existing data and
never changes the hardware. The fit quality is printed to stdout so you can spot
a bad curve.

## 4. When to recalibrate

Recalibrate when the physical liquid path changes or drifts: after replacing or
re-seating tubing or a valve, if dispensed volumes look off, or if a plotted
curve fits poorly. Routinely, a periodic recalibration keeps reward volumes
honest across long training pipelines.

## You now know

Valve calibration measures each valve's open-time-to-volume relationship and
stores it per rig in the setup YAML, run as the `_calibration_liquid_*` tasks.
`msw calibration plot` saves the fitted curves as PDF, and you recalibrate
whenever the liquid path changes or a curve fits poorly.

## Next

You have reached the end of the tutorial series. For the calibration
troubleshooting table and YAML details, see
[Valve Calibration](calibration.md).
