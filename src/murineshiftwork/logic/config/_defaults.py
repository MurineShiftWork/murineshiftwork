from murineshiftwork.logic.config.models import ValveCalibration

# Fallback used when a setup has no valve calibration at all.
# Generic approximate values — for debug/smoke-test runs only.
# Do not use for experiments; calibrate the actual setup first.
_FALLBACK_VALVE_CALIBRATION = ValveCalibration(
    updated="2026-06-01",
    points=[
        [0.010, 1.0],
        [0.030, 3.0],
        [0.060, 7.0],
        [0.100, 12.0],
        [0.150, 20.0],
    ],
)
