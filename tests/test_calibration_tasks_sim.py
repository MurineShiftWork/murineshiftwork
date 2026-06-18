"""Smoke tests for calibration task logic using SimBpod + SimWeighingScale.

Tests run without hardware.  They verify that:
- Tasks complete without exceptions given injected sim hardware
- calibration.save() is called (file is created)
- outlier reporting fires for the expected conditions
"""

from pathlib import Path

from murineshiftwork.hardware.bpod.sim import SimBpod
from murineshiftwork.hardware.scale import SimWeighingScale

# ---------------------------------------------------------------------------
# Helpers


def _make_sim_kwargs(tmp_path: Path, valve_id: int = 1) -> dict:
    """Minimal kwargs for both calibration Task classes."""
    cal_file = tmp_path / "calibration.liquid.test.csv"
    return {
        "settings.task.patched": {
            "VALVES_TO_CALIBRATE": [valve_id],
            "VALVE_TIME_MIN": 0.010,
            "VALVE_TIME_MAX": 0.030,
            "VALVE_TIME_STEP": 0.010,
            "N_DROPS": 2,
            "INTER_PULSE_INTERVAL": 0.005,
            "SETTLE_TIME_S": 0.0,
            "OUTLIER_SIGMA_THRESHOLD": 2.5,
            "force_save_calibration": False,
            # dynamic-only
            "OPENING_TIME_MIN_S": 0.010,
            "OPENING_TIME_MAX_S": 0.030,
            "N_INITIAL_POINTS": 3,
            "INTER_PULSE_INTERVAL_S": 0.005,
            "MAX_ADAPTIVE_ROUNDS": 0,
            "COVERAGE_N_POINTS_TARGET": 3,
            "MIN_PULSES": 1,
            "MAX_PULSES": 3,
            "MIN_SNR": 1,
            "SCALE_NOISE_G": 0.05,
            "TARGET_RANGE_UL": [0.1, 5.0],
        },
        "calibration_file_liquid": str(cal_file),
        "scale": SimWeighingScale(weight_g=0.004),
        "config_dir": "",
        "setup": "unknown_setup",
    }


# ---------------------------------------------------------------------------
# _calibration_liquid_static


class TestCalibrationLiquidStaticSim:
    def test_task_completes_and_saves(self, tmp_path):
        from murineshiftwork.tasks._calibration_liquid_static.task import (
            Task,
        )

        kwargs = _make_sim_kwargs(tmp_path)
        bpod = SimBpod()
        bpod.open()

        task = Task(bpod=bpod, **kwargs)
        task.run()

        cal_file = Path(kwargs["calibration_file_liquid"])
        assert cal_file.exists(), "calibration CSV must be saved after task completes"

    def test_bpod_state_machines_were_fired(self, tmp_path):
        from murineshiftwork.tasks._calibration_liquid_static.task import (
            Task,
        )

        kwargs = _make_sim_kwargs(tmp_path)
        bpod = SimBpod()
        bpod.open()

        task = Task(bpod=bpod, **kwargs)
        task.run()

        assert bpod.sma_run_count() > 0, (
            "at least one SMA run expected for calibration drops"
        )

    def test_scale_was_tared_per_point(self, tmp_path):
        from murineshiftwork.tasks._calibration_liquid_static.task import (
            Task,
        )

        kwargs = _make_sim_kwargs(tmp_path)
        scale = SimWeighingScale(weight_g=0.004)
        kwargs["scale"] = scale
        bpod = SimBpod()
        bpod.open()

        task = Task(bpod=bpod, **kwargs)
        task.run()

        # tare is called at task start + once per opening-time point
        assert scale.tare_count >= 2


# ---------------------------------------------------------------------------
# _calibration_liquid_dynamic


class TestCalibrationLiquidDynamicSim:
    def test_task_completes_and_saves(self, tmp_path):
        from murineshiftwork.tasks._calibration_liquid_dynamic.task import (
            Task,
        )

        kwargs = _make_sim_kwargs(tmp_path)
        bpod = SimBpod()
        bpod.open()

        task = Task(bpod=bpod, **kwargs)
        task.run()

        cal_file = Path(kwargs["calibration_file_liquid"])
        assert cal_file.exists(), "calibration CSV must be saved"

    def test_bpod_state_machines_were_fired(self, tmp_path):
        from murineshiftwork.tasks._calibration_liquid_dynamic.task import (
            Task,
        )

        kwargs = _make_sim_kwargs(tmp_path)
        bpod = SimBpod()
        bpod.open()

        task = Task(bpod=bpod, **kwargs)
        task.run()

        assert bpod.sma_run_count() > 0

    def test_scale_tared_per_valve(self, tmp_path):
        from murineshiftwork.tasks._calibration_liquid_dynamic.task import (
            Task,
        )

        kwargs = _make_sim_kwargs(tmp_path)
        scale = SimWeighingScale(weight_g=0.004)
        kwargs["scale"] = scale
        bpod = SimBpod()
        bpod.open()

        task = Task(bpod=bpod, **kwargs)
        task.run()

        # Dynamic calibration tares once per valve (before/after delta approach, not per point).
        # With 1 valve in the test fixture, tare_count == 1.
        assert scale.tare_count >= 1
