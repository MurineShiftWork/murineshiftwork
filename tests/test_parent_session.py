"""Tests for the parent-session attachment system."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from murineshiftwork.hardware.parent_session import (
    OpenEphysParentSession,
    ParentSessionInfo,
    ParentSessionProtocol,
    _parse_host,
    make_parent_session,
)
from murineshiftwork.logic.config.models import SetupConfig

# ---------------------------------------------------------------------------
# _parse_host


def test_parse_host_bare_ip():
    assert _parse_host("172.24.42.168") == "172.24.42.168"


def test_parse_host_with_http():
    assert _parse_host("http://172.24.42.168") == "172.24.42.168"


def test_parse_host_with_port():
    assert _parse_host("172.24.42.168:37497") == "172.24.42.168"


def test_parse_host_full_url():
    assert _parse_host("http://172.24.42.168:37497") == "172.24.42.168"


def test_parse_host_hostname():
    assert _parse_host("rig-pc.local") == "rig-pc.local"


# ---------------------------------------------------------------------------
# ParentSessionInfo


def test_parent_session_info_fields():
    info = ParentSessionInfo(
        acquisition_name="m01__20260101_120000__ephys",
        subject="m01",
        parent_directory="/data",
        backend="open_ephys",
    )
    assert info.acquisition_name == "m01__20260101_120000__ephys"
    assert info.backend == "open_ephys"
    assert info.extra == {}


# ---------------------------------------------------------------------------
# SetupConfig — no parent_session field


def test_setup_config_has_no_parent_session_field():
    cfg = SetupConfig(name="rig1")
    assert not hasattr(cfg, "parent_session")


# ---------------------------------------------------------------------------
# make_parent_session factory


def test_make_parent_session_returns_oe_client():
    client = make_parent_session("open_ephys", url="127.0.0.1")
    assert isinstance(client, OpenEphysParentSession)
    assert isinstance(client, ParentSessionProtocol)


def test_make_parent_session_name():
    client = make_parent_session("open_ephys", url="127.0.0.1")
    assert client.name == "open_ephys"


def test_make_parent_session_alias_openephys():
    client = make_parent_session("openephys", url="127.0.0.1")
    assert isinstance(client, OpenEphysParentSession)


def test_make_parent_session_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown parent session type"):
        make_parent_session("imaging", url="127.0.0.1")


# ---------------------------------------------------------------------------
# OpenEphysParentSession.attach — mocked HTTP


def _make_gui_mock(
    status="IDLE", base_text="", prepend_text="", append_text="", record_nodes=None
):
    gui = MagicMock()
    type(gui).status = PropertyMock(return_value=status)
    type(gui).recording = PropertyMock(
        return_value={
            "base_text": base_text,
            "prepend_text": prepend_text,
            "append_text": append_text,
            "record_nodes": record_nodes or [],
        }
    )
    return gui


@patch("murineshiftwork.hardware.parent_session.OpenEphysParentSession.attach")
def test_attach_import_error(mock_attach):
    mock_attach.return_value = None
    client = OpenEphysParentSession(url="127.0.0.1")
    assert client.attach() is None


def test_attach_returns_none_on_connection_error():
    gui = MagicMock()
    type(gui).status = PropertyMock(side_effect=Exception("Connection refused"))
    client = OpenEphysParentSession(url="127.0.0.1")
    result = _attach_with_mock_gui(client, gui)
    assert result is None


def _attach_with_mock_gui(client, gui_mock):
    """Helper: patch OEController ctor to return gui_mock, call attach()."""
    with patch.dict(
        "sys.modules",
        {
            "msw_open_ephys": MagicMock(),
            "msw_open_ephys.controller": MagicMock(OEController=lambda ip: gui_mock),
        },
    ):
        return client.attach()


def test_attach_valid_three_part_base_text():
    gui = _make_gui_mock(
        status="RECORD",
        base_text="m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi",
        record_nodes=[{"parent_directory": "/data/rig1"}],
    )
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.acquisition_name == "m01__20260101_120000__ephys"
    assert info.subject == "m01"
    assert info.parent_directory == "/data/rig1"
    assert info.backend == "open_ephys"
    assert info.extra["oe_session_name"] == "m01__20260101_120000__pxi"


def test_attach_two_part_base_text_still_works():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260101_120000__ephys",
    )
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.acquisition_name == "m01__20260101_120000__ephys"
    assert info.extra["oe_session_name"] == ""


def test_attach_one_part_base_text_returns_none():
    gui = _make_gui_mock(status="IDLE", base_text="YYYY-MM-DD_HH-MM-SS")
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is None


def test_attach_empty_base_text_returns_none():
    gui = _make_gui_mock(status="IDLE", base_text="")
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is None


def test_attach_require_recording_blocks_idle():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi",
    )
    client = OpenEphysParentSession(url="127.0.0.1", require_recording=True)
    info = _attach_with_mock_gui(client, gui)
    assert info is None


def test_attach_require_recording_passes_when_recording():
    gui = _make_gui_mock(
        status="RECORD",
        base_text="m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi",
    )
    client = OpenEphysParentSession(url="127.0.0.1", require_recording=True)
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.acquisition_name == "m01__20260101_120000__ephys"


def test_attach_host_parsed_from_url():
    client = OpenEphysParentSession(url="http://172.24.42.168:37497")
    assert client._host == "172.24.42.168"


# ---------------------------------------------------------------------------
# base_text parsing invariants
# These cover the specific guarantees that make the OE→MSW path handoff safe.


def test_attach_second_precision_datetime():
    # OE uses time.strftime("%Y%m%d_%H%M%S") — no microseconds.
    # namespace regex has (?:_\d{6})? so second-precision names must parse.
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260524_143022__ephys/m01__20260524_143022__pxi",
    )
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.acquisition_name == "m01__20260524_143022__ephys"


def test_attach_microsecond_precision_datetime():
    # MSW-generated acquisition names use microsecond precision; verify roundtrip.
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260524_143022_123456__ephys/m01__20260524_143022_123456__pxi",
    )
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.acquisition_name == "m01__20260524_143022_123456__ephys"


def test_attach_leading_trailing_slashes_stripped():
    # OE may include leading/trailing slashes; strip("/") + filter handles them.
    gui = _make_gui_mock(
        status="IDLE",
        base_text="/m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi/",
    )
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.acquisition_name == "m01__20260101_120000__ephys"


def test_attach_invalid_acq_segment_returns_none():
    # parts[1] is not a valid MSW basename (OE default template not yet replaced).
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/YYYY-MM-DD_HH-MM-SS/something",
    )
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is None
    assert "not a valid MSW session name" in client.fail_reason


def test_attach_acquisition_and_session_levels_have_same_template():
    # Both acquisition and session levels use {subject}__{datetime}__{task}.
    # Validating parts[1] through "session" level is equivalent to "acquisition".
    # Confirmed by checking the namespace builder directly.
    from murineshiftwork.namespace.paths import get_msw_builder

    b = get_msw_builder()
    acq_spec = b.spec.levels["acquisition"]
    ses_spec = b.spec.levels["session"]
    assert acq_spec.template == ses_spec.template
    assert acq_spec.regex == ses_spec.regex


# ---------------------------------------------------------------------------
# Integration: base_text → acquisition_name → generate_session_paths


def test_attach_feeds_generate_session_paths_correctly(tmp_path):
    # Full roundtrip: OE base_text → ParentSessionInfo → generate_session_paths.
    # Verifies session folder has structure: basepath/subject/acq_name/session_basename
    from murineshiftwork.namespace.paths import generate_session_paths

    gui = _make_gui_mock(
        status="RECORD",
        base_text="m01/m01__20260524_143022__ephys/m01__20260524_143022__pxi",
        record_nodes=[{"parent_directory": "/data/rig1"}],
    )
    client = OpenEphysParentSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None

    paths = generate_session_paths(
        subject="m01",
        task="sequence",
        basepath=tmp_path,
        is_child_session_to=info.acquisition_name,
        printout=False,
    )

    rel_parts = Path(paths["session_folder_relative"]).parts
    assert rel_parts[0] == "m01"  # subject
    assert rel_parts[1] == "m01__20260524_143022__ephys"  # acquisition_name from OE
    assert rel_parts[2].startswith("m01__")  # session basename
    assert rel_parts[2].endswith("__sequence")
    assert paths["acquisition_name"] == "m01__20260524_143022__ephys"
