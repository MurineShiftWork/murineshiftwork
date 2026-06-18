"""Tests for namespace.manifest: acquisition and session manifest writers."""

import yaml
from murineshiftwork.namespace.manifest import (
    append_session_to_acquisition,
    append_subprotocol,
    finalize_session_in_acquisition,
    finalize_subprotocol,
    init_acquisition_manifest,
    init_session_manifest,
)

# ---------------------------------------------------------------------------
# Acquisition manifest


def test_init_acquisition_manifest_creates_file(tmp_path):
    init_acquisition_manifest(tmp_path, "mouse_01__20260527__session_sequence")
    p = tmp_path / "acquisition_manifest.yaml"
    assert p.exists()
    data = yaml.safe_load(p.read_text())
    assert data["type"] == "acquisition"
    assert data["msw_manifest_version"] == 1
    assert data["sessions"] == []


def test_init_acquisition_manifest_idempotent(tmp_path):
    init_acquisition_manifest(tmp_path, "acq_a")
    init_acquisition_manifest(tmp_path, "acq_b")  # second call must not overwrite
    data = yaml.safe_load((tmp_path / "acquisition_manifest.yaml").read_text())
    assert data["acquisition_name"] == "acq_a"


def test_append_session_adds_entry(tmp_path):
    init_acquisition_manifest(tmp_path, "acq")
    append_session_to_acquisition(tmp_path, "mouse_01__20260527__sequence")
    data = yaml.safe_load((tmp_path / "acquisition_manifest.yaml").read_text())
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["basename"] == "mouse_01__20260527__sequence"
    assert data["sessions"][0]["status"] == "running"


def test_append_session_does_not_duplicate(tmp_path):
    init_acquisition_manifest(tmp_path, "acq")
    append_session_to_acquisition(tmp_path, "mouse_01__20260527__sequence")
    append_session_to_acquisition(tmp_path, "mouse_01__20260527__sequence")
    data = yaml.safe_load((tmp_path / "acquisition_manifest.yaml").read_text())
    assert len(data["sessions"]) == 1


def test_finalize_session_sets_status_and_time(tmp_path):
    init_acquisition_manifest(tmp_path, "acq")
    append_session_to_acquisition(tmp_path, "mouse_01__20260527__sequence")
    finalize_session_in_acquisition(
        tmp_path, "mouse_01__20260527__sequence", status="complete"
    )
    data = yaml.safe_load((tmp_path / "acquisition_manifest.yaml").read_text())
    s = data["sessions"][0]
    assert s["status"] == "complete"
    assert s["ended_at"] is not None


def test_finalize_session_aborted(tmp_path):
    init_acquisition_manifest(tmp_path, "acq")
    append_session_to_acquisition(tmp_path, "basename")
    finalize_session_in_acquisition(tmp_path, "basename", status="aborted")
    data = yaml.safe_load((tmp_path / "acquisition_manifest.yaml").read_text())
    assert data["sessions"][0]["status"] == "aborted"


def test_finalize_session_missing_manifest_is_noop(tmp_path):
    # Should not raise even if manifest was never written
    finalize_session_in_acquisition(tmp_path, "basename")


# ---------------------------------------------------------------------------
# Session manifest


def test_init_session_manifest_creates_file(tmp_path):
    init_session_manifest(tmp_path, "mouse_01__20260527__optotagging")
    p = tmp_path / "session_manifest.yaml"
    assert p.exists()
    data = yaml.safe_load(p.read_text())
    assert data["type"] == "session"
    assert data["subprotocols"] == []


def test_init_session_manifest_idempotent(tmp_path):
    init_session_manifest(tmp_path, "basename_a")
    init_session_manifest(tmp_path, "basename_b")
    data = yaml.safe_load((tmp_path / "session_manifest.yaml").read_text())
    assert data["session_basename"] == "basename_a"


def test_append_subprotocol_adds_entry(tmp_path):
    init_session_manifest(tmp_path, "basename")
    append_subprotocol(
        tmp_path, "power_ramp", "basename_power_ramp.msw.df.jsonl", barcode_start=42
    )
    data = yaml.safe_load((tmp_path / "session_manifest.yaml").read_text())
    assert len(data["subprotocols"]) == 1
    sp = data["subprotocols"][0]
    assert sp["name"] == "power_ramp"
    assert sp["barcode_start"] == 42
    assert sp["status"] == "running"
    assert sp["barcode_end"] is None


def test_append_multiple_subprotocols(tmp_path):
    init_session_manifest(tmp_path, "basename")
    append_subprotocol(tmp_path, "power_ramp", "f1.msw.df.jsonl", barcode_start=10)
    append_subprotocol(tmp_path, "following_test", "f2.msw.df.jsonl", barcode_start=12)
    data = yaml.safe_load((tmp_path / "session_manifest.yaml").read_text())
    assert len(data["subprotocols"]) == 2


def test_append_subprotocol_does_not_duplicate(tmp_path):
    init_session_manifest(tmp_path, "basename")
    append_subprotocol(tmp_path, "power_ramp", "f.msw.df.jsonl")
    append_subprotocol(tmp_path, "power_ramp", "f.msw.df.jsonl")
    data = yaml.safe_load((tmp_path / "session_manifest.yaml").read_text())
    assert len(data["subprotocols"]) == 1


def test_finalize_subprotocol_sets_barcode_and_status(tmp_path):
    init_session_manifest(tmp_path, "basename")
    append_subprotocol(tmp_path, "power_ramp", "f.msw.df.jsonl", barcode_start=10)
    finalize_subprotocol(tmp_path, "power_ramp", barcode_end=11, status="complete")
    data = yaml.safe_load((tmp_path / "session_manifest.yaml").read_text())
    sp = data["subprotocols"][0]
    assert sp["barcode_end"] == 11
    assert sp["status"] == "complete"


def test_finalize_subprotocol_aborted(tmp_path):
    init_session_manifest(tmp_path, "basename")
    append_subprotocol(tmp_path, "power_ramp", "f.msw.df.jsonl")
    finalize_subprotocol(tmp_path, "power_ramp", status="aborted")
    data = yaml.safe_load((tmp_path / "session_manifest.yaml").read_text())
    assert data["subprotocols"][0]["status"] == "aborted"


def test_finalize_subprotocol_missing_manifest_is_noop(tmp_path):
    finalize_subprotocol(tmp_path, "power_ramp")


def test_full_opto_lifecycle(tmp_path):
    """End-to-end: acquisition + session + two protocols, all finalized."""
    init_acquisition_manifest(tmp_path, "mouse_01__20260527__session_optotagging")
    append_session_to_acquisition(tmp_path, "mouse_01__20260527__optotagging")

    session_dir = tmp_path / "mouse_01__20260527__optotagging"
    session_dir.mkdir()
    init_session_manifest(session_dir, "mouse_01__20260527__optotagging")

    for proto, bc_s, bc_e in [("power_ramp", 10, 11), ("following_test", 12, 13)]:
        fname = f"mouse_01__20260527__optotagging_{proto}.msw.df.jsonl"
        append_subprotocol(session_dir, proto, fname, barcode_start=bc_s)
        finalize_subprotocol(session_dir, proto, barcode_end=bc_e)

    finalize_session_in_acquisition(
        tmp_path, "mouse_01__20260527__optotagging", status="complete"
    )

    acq = yaml.safe_load((tmp_path / "acquisition_manifest.yaml").read_text())
    ses = yaml.safe_load((session_dir / "session_manifest.yaml").read_text())

    assert acq["sessions"][0]["status"] == "complete"
    assert len(ses["subprotocols"]) == 2
    assert ses["subprotocols"][0]["barcode_end"] == 11
    assert ses["subprotocols"][1]["barcode_start"] == 12
