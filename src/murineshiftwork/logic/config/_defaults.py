from murineshiftwork.logic.config.models import ValveCalibration

# Fallback used when a setup has no valve calibration at all.
# Derived from setup-npx2 valve 2 (2026-05-18).  Debug use only.
_FALLBACK_VALVE_CALIBRATION = ValveCalibration(
    updated="2026-05-18",
    points=[
        [0.005, 0.3],
        [0.034, 3.4],
        [0.041, 4.5],
        [0.077, 10.7],
        [0.102, 13.0],
        [0.150, 21.2],
    ],
)
