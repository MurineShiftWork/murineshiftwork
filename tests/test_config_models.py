"""Tests for config_models: ValveCalibration, SetupConfig, SubjectConfig."""

import pytest

from murineshiftwork.logic.config import (
    BpodDevice,
    Calibrations,
    ExecutionConfig,
    SetupConfig,
    SubjectConfig,
    ValveCalibration,
)

# ---------------------------------------------------------------------------
# ValveCalibration — fit and lookup

POINTS_SETUP1_VALVE1 = [
    [0.010, 0.55],
    [0.028, 1.15],
    [0.046, 1.425],
    [0.064, 1.675],
    [0.082, 1.925],
]

POINTS_SETUP3_VALVE1 = [
    [0.010, 0.675],
    [0.028, 2.075],
    [0.046, 4.15],
    [0.064, 6.525],
    [0.082, 9.05],
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
    vc = ValveCalibration(
        points=[
            [10.0, 1.0],
            [20.0, 0.5],
            [30.0, 1.5],
            [40.0, 2.0],
            [50.0, 2.5],
        ]
    )
    ok, reason = vc.validate()
    assert not ok
    assert "monoton" in reason.lower()


def test_valve_calibration_ul_for_s_increases():
    vc = ValveCalibration(points=POINTS_SETUP3_VALVE1)
    v10 = vc.ul_for_s(0.010)
    v50 = vc.ul_for_s(0.050)
    v80 = vc.ul_for_s(0.080)
    assert v10 < v50 < v80


def test_valve_calibration_s_for_ul_roundtrip():
    vc = ValveCalibration(points=POINTS_SETUP3_VALVE1)
    target_ul = 3.0
    s = vc.s_for_ul(target_ul)
    recovered = vc.ul_for_s(s)
    assert abs(recovered - target_ul) < 0.1


def test_valve_calibration_s_for_ul_within_range():
    vc = ValveCalibration(points=POINTS_SETUP3_VALVE1)
    s = vc.s_for_ul(2.0)
    assert 0.010 <= s <= 0.082


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


def test_setup_valve_ul_for_s():
    s = _make_setup()
    ul = s.valve_ul_for_s(1, 0.046)
    assert 3.5 < ul < 5.0


def test_setup_valve_s_for_ul():
    s = _make_setup()
    open_s = s.valve_s_for_ul(1, 4.0)
    assert 0.040 < open_s < 0.060


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
        task_overrides={"_test_flush_valves": {"VALVE_OPENING_TIME_MS": 80}},
    )
    assert sc.task_overrides["_test_flush_valves"]["VALVE_OPENING_TIME_MS"] == 80


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
        task_name="_test_flush_valves",
        task_settings={"VALVE_OPENING_TIME_MS": 60},
    )
    assert ec.setup.name == "test_setup"
    assert ec.subject.name == "mouse_01"
    assert ec.task_settings["VALVE_OPENING_TIME_MS"] == 60
