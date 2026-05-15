"""Tests for config_models: ValveCalibration, SetupConfig, SubjectConfig."""
import pytest
import numpy as np

from murineshiftwork.logic.config import (
    AxisConfig,
    BpodDevice,
    Calibrations,
    CameraConfig,
    ExecutionConfig,
    SetupConfig,
    StageTowerDevice,
    SubjectConfig,
    ValveCalibration,
)


# ---------------------------------------------------------------------------
# ValveCalibration — fit and lookup

POINTS_SETUP1_VALVE1 = [
    [10.0, 0.55], [28.0, 1.15], [46.0, 1.425], [64.0, 1.675], [82.0, 1.925]
]

POINTS_SETUP3_VALVE1 = [
    [10.0, 0.675], [28.0, 2.075], [46.0, 4.15], [64.0, 6.525], [82.0, 9.05]
]


def test_valve_calibration_validate_pass():
    vc = ValveCalibration(points=POINTS_SETUP3_VALVE1)
    ok, reason = vc.validate()
    assert ok, reason


def test_valve_calibration_validate_too_few_points():
    vc = ValveCalibration(points=[[10.0, 0.5], [20.0, 1.0]])
    ok, reason = vc.validate()
    assert not ok
    assert "3" in reason


def test_valve_calibration_validate_non_monotonic():
    vc = ValveCalibration(points=[[10.0, 1.0], [20.0, 0.5], [30.0, 1.5], [40.0, 2.0], [50.0, 2.5]])
    ok, reason = vc.validate()
    assert not ok
    assert "monoton" in reason.lower()


def test_valve_calibration_ul_for_ms_increases():
    vc = ValveCalibration(points=POINTS_SETUP3_VALVE1)
    v10 = vc.ul_for_ms(10.0)
    v50 = vc.ul_for_ms(50.0)
    v80 = vc.ul_for_ms(80.0)
    assert v10 < v50 < v80


def test_valve_calibration_ms_for_ul_roundtrip():
    vc = ValveCalibration(points=POINTS_SETUP3_VALVE1)
    target_ul = 3.0
    ms = vc.ms_for_ul(target_ul)
    recovered = vc.ul_for_ms(ms)
    assert abs(recovered - target_ul) < 0.1


def test_valve_calibration_ms_for_ul_within_range():
    vc = ValveCalibration(points=POINTS_SETUP3_VALVE1)
    ms = vc.ms_for_ul(2.0)
    assert 10.0 <= ms <= 82.0


def test_valve_calibration_updated_preserved():
    vc = ValveCalibration(updated="2025-08-07T10:11:56", points=POINTS_SETUP1_VALVE1)
    assert vc.updated == "2025-08-07T10:11:56"


# ---------------------------------------------------------------------------
# SetupConfig

def _make_setup():
    return SetupConfig(
        name="test_setup",
        devices={
            "bpod": BpodDevice(type="bpod", port_by_path="some-path"),
        },
        calibrations=Calibrations(
            bpod_valve={
                "1": ValveCalibration(points=POINTS_SETUP3_VALVE1),
            }
        ),
    )


def test_setup_config_name():
    s = _make_setup()
    assert s.name == "test_setup"


def test_setup_valve_ul_for_ms():
    s = _make_setup()
    ul = s.valve_ul_for_ms(1, 46.0)
    assert 3.5 < ul < 5.0


def test_setup_valve_ms_for_ul():
    s = _make_setup()
    ms = s.valve_ms_for_ul(1, 4.0)
    assert 40.0 < ms < 60.0


def test_setup_device_port_missing():
    s = _make_setup()
    with pytest.raises(KeyError):
        s.device_port("stage")


# ---------------------------------------------------------------------------
# SubjectConfig

def test_subject_config_defaults():
    sc = SubjectConfig(name="test_mouse")
    assert sc.registered == ""
    assert sc.task_overrides == {}
    assert sc.aliases == []


def test_subject_config_task_overrides():
    sc = SubjectConfig(
        name="test_mouse",
        task_overrides={"_test_flush_water": {"VALVE_OPENING_TIME_MS": 80}},
    )
    assert sc.task_overrides["_test_flush_water"]["VALVE_OPENING_TIME_MS"] == 80


# ---------------------------------------------------------------------------
# ExecutionConfig

def test_execution_config_defaults():
    ec = ExecutionConfig()
    assert ec.setup is None
    assert ec.subject is None
    assert ec.task_name == ""
    assert ec.task_settings == {}


def test_execution_config_with_setup_and_subject():
    ec = ExecutionConfig(
        setup=_make_setup(),
        subject=SubjectConfig(name="mouse_01"),
        task_name="_test_flush_water",
        task_settings={"VALVE_OPENING_TIME_MS": 60},
    )
    assert ec.setup.name == "test_setup"
    assert ec.subject.name == "mouse_01"
    assert ec.task_settings["VALVE_OPENING_TIME_MS"] == 60
