"""Tests for msw post clean, run_action dispatch, and save_calibration_pdfs."""

import pytest
import yaml

# ---------------------------------------------------------------------------
# msw post clean


def test_post_clean_removes_event_rows(tmp_path):
    from murineshiftwork.cli.post import run_post_clean

    f = tmp_path / "session.msw.csv"
    f.write_text("header\nPort4In,1.0\nPort1In,2.0\nPort4Out,3.0\n")
    run_post_clean(data_dir=str(tmp_path), event="Port4", dry_run=False)
    cleaned = f.read_text()
    assert "Port4" not in cleaned
    assert "Port1In" in cleaned


def test_post_clean_dry_run_does_not_modify(tmp_path):
    from murineshiftwork.cli.post import run_post_clean

    f = tmp_path / "session.msw.csv"
    original = "header\nPort4In,1.0\n"
    f.write_text(original)
    run_post_clean(data_dir=str(tmp_path), event="Port4", dry_run=True)
    assert f.read_text() == original


def test_post_clean_no_matching_event_leaves_file_unchanged(tmp_path):
    from murineshiftwork.cli.post import run_post_clean

    f = tmp_path / "session.msw.csv"
    original = "header\nPort1In,1.0\n"
    f.write_text(original)
    run_post_clean(data_dir=str(tmp_path), event="Port4", dry_run=False)
    assert f.read_text() == original
    # no backup created when nothing to clean
    assert not list(tmp_path.glob("*.bak.*"))


def test_post_clean_creates_backup(tmp_path):
    from murineshiftwork.cli.post import run_post_clean

    f = tmp_path / "session.msw.csv"
    f.write_text("header\nPort4In,1.0\n")
    run_post_clean(data_dir=str(tmp_path), event="Port4", dry_run=False)
    backups = list(tmp_path.glob("*.bak.*"))
    assert len(backups) == 1


def test_post_clean_missing_data_dir_raises(tmp_path):
    from murineshiftwork.cli.post import run_post_clean

    with pytest.raises(FileNotFoundError):
        run_post_clean(
            data_dir=str(tmp_path / "nonexistent"), event="Port4", dry_run=False
        )


def test_post_clean_recurses_into_subdirectories(tmp_path):
    from murineshiftwork.cli.post import run_post_clean

    sub = tmp_path / "mouse001" / "2025-01-01"
    sub.mkdir(parents=True)
    f = sub / "session.msw.csv"
    f.write_text("header\nPort4In,1.0\nPort1In,2.0\n")
    run_post_clean(data_dir=str(tmp_path), event="Port4", dry_run=False)
    assert "Port4" not in f.read_text()
    assert "Port1In" in f.read_text()


# ---------------------------------------------------------------------------
# run_action: mocked BpodFactory to avoid hardware


def _make_sim_setup_yaml(tmp_path, setup_name="test_setup"):
    (tmp_path / "setups").mkdir(exist_ok=True)
    data = {
        "name": setup_name,
        "devices": {"bpod": {"type": "bpod", "port_by_path": "test-path"}},
        "calibrations": {"bpod_valve": {}},
    }
    path = tmp_path / "setups" / f"{setup_name}.yaml"
    path.write_text(yaml.dump(data))
    return str(tmp_path)


def test_run_action_dispatches_valve_pulse(tmp_path, monkeypatch):
    """run_action wires up correctly; BpodFactory and driver are mocked."""
    from murineshiftwork.hardware.bpod.sim import SimBpod

    sim = SimBpod()
    sim.open()

    import murineshiftwork.cli.execute as exe

    # Patch BpodFactory context manager to return SimBpod
    class _FakeFactory:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return sim

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(exe, "BpodFactory", _FakeFactory, raising=False)

    # Also patch the import inside run_action
    import murineshiftwork.hardware.bpod.factory as fmod

    monkeypatch.setattr(fmod, "BpodFactory", _FakeFactory)

    config_dir = _make_sim_setup_yaml(tmp_path)
    monkeypatch.setattr(
        "murineshiftwork.logic.machine_config.resolve_config_dir",
        lambda cli_override="": config_dir,
    )

    from murineshiftwork.cli.execute import run_action

    # Should not raise; pass minimal params so time.sleep totals <50 ms
    run_action(
        setup="test_setup",
        device="bpod",
        action="valve_pulse",
        params=["valve_id=1", "duration_s=0.001"],
        config_dir=config_dir,
        serial_port_bpod="/dev/null",
    )


def test_run_action_unknown_setup_raises(tmp_path, monkeypatch):
    config_dir = _make_sim_setup_yaml(tmp_path)
    monkeypatch.setattr(
        "murineshiftwork.logic.machine_config.resolve_config_dir",
        lambda cli_override="": config_dir,
    )
    from murineshiftwork.cli.execute import run_action

    with pytest.raises(ValueError, match="not found"):
        run_action(
            setup="nonexistent_setup",
            device="bpod",
            action="valve_pulse",
            params=[],
            config_dir=config_dir,
            serial_port_bpod="/dev/null",
        )


def test_run_action_unknown_device_raises(tmp_path, monkeypatch):
    config_dir = _make_sim_setup_yaml(tmp_path)
    monkeypatch.setattr(
        "murineshiftwork.logic.machine_config.resolve_config_dir",
        lambda cli_override="": config_dir,
    )
    from murineshiftwork.cli.execute import run_action

    with pytest.raises(KeyError, match="stage"):
        run_action(
            setup="test_setup",
            device="stage",
            action="move",
            params=[],
            config_dir=config_dir,
            serial_port_bpod="/dev/null",
        )


def test_run_action_unsupported_device_type_raises(tmp_path, monkeypatch):
    (tmp_path / "setups").mkdir(exist_ok=True)
    data = {
        "name": "cam_setup",
        "devices": {"camera": {"type": "flir", "serial": "12345"}},
        "calibrations": {},
    }
    (tmp_path / "setups" / "cam_setup.yaml").write_text(yaml.dump(data))
    monkeypatch.setattr(
        "murineshiftwork.logic.machine_config.resolve_config_dir",
        lambda cli_override="": str(tmp_path),
    )
    from murineshiftwork.cli.execute import run_action

    with pytest.raises((ValueError, Exception)):
        run_action(
            setup="cam_setup",
            device="camera",
            action="snap",
            params=[],
            config_dir=str(tmp_path),
            serial_port_bpod="/dev/null",
        )


# ---------------------------------------------------------------------------
# save_calibration_pdfs smoke test


POINTS_VALID = [
    [0.010, 0.675],
    [0.028, 2.075],
    [0.046, 4.15],
    [0.064, 6.525],
    [0.082, 9.05],
]


def test_save_calibration_pdfs_creates_pdf(tmp_path):
    from murineshiftwork.logic.calibration import save_calibration_pdfs

    (tmp_path / "setups").mkdir()
    setup_data = {
        "name": "test_setup",
        "devices": {},
        "calibrations": {
            "bpod_valve": {
                "1": {"updated": "2025-08-07T10:00:00", "points": POINTS_VALID},
                "3": {"updated": "2025-08-07T10:00:00", "points": POINTS_VALID},
            }
        },
    }
    (tmp_path / "setups" / "test_setup.yaml").write_text(yaml.dump(setup_data))
    out = tmp_path / "pdfs"
    saved = save_calibration_pdfs(config_dir=str(tmp_path), output_dir=str(out))
    assert len(saved) == 1
    assert saved[0].endswith(".pdf")


def test_save_calibration_pdfs_skips_setup_without_valve_data(tmp_path):
    from murineshiftwork.logic.calibration import save_calibration_pdfs

    (tmp_path / "setups").mkdir()
    setup_data = {
        "name": "empty_setup",
        "devices": {},
        "calibrations": {"bpod_valve": {}},
    }
    (tmp_path / "setups" / "empty_setup.yaml").write_text(yaml.dump(setup_data))
    saved = save_calibration_pdfs(config_dir=str(tmp_path), output_dir=str(tmp_path))
    assert saved == []


def test_save_calibration_pdfs_single_setup_filter(tmp_path):
    from murineshiftwork.logic.calibration import save_calibration_pdfs

    (tmp_path / "setups").mkdir()
    for name in ("setup_a", "setup_b"):
        d = {
            "name": name,
            "devices": {},
            "calibrations": {
                "bpod_valve": {
                    "1": {"updated": "2025-08-07T10:00:00", "points": POINTS_VALID}
                }
            },
        }
        (tmp_path / "setups" / f"{name}.yaml").write_text(yaml.dump(d))
    saved = save_calibration_pdfs(
        config_dir=str(tmp_path), setup_name="setup_a", output_dir=str(tmp_path)
    )
    assert len(saved) == 1
    assert "setup_a" in saved[0]
