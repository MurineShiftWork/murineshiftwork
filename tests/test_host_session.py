"""Tests for the host-session plugin system."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

msw_open_ephys = pytest.importorskip("msw_open_ephys")
from msw_open_ephys.host import OpenEphysHostSession, _parse_host  # noqa: E402
from msw_plugin_api import HostSessionInfo, HostSessionProtocol  # noqa: E402
from murineshiftwork.logic.config.models import SetupConfig  # noqa: E402

# ---------------------------------------------------------------------------
# _parse_host


def test_parse_host_bare_ip():
    assert _parse_host("10.0.10.111") == "10.0.10.111"


def test_parse_host_with_http():
    assert _parse_host("http://10.0.10.111") == "10.0.10.111"


def test_parse_host_with_port():
    assert _parse_host("10.0.10.111:37497") == "10.0.10.111"


def test_parse_host_full_url():
    assert _parse_host("http://10.0.10.111:37497") == "10.0.10.111"


def test_parse_host_hostname():
    assert _parse_host("rig-pc.local") == "rig-pc.local"


# ---------------------------------------------------------------------------
# HostSessionInfo / HostSessionProtocol


def test_host_session_info_fields():
    info = HostSessionInfo(
        backend="openephys",
        session_name="m01__20260101_120000__ephys",
        subject="m01",
        parent_directory="/data",
    )
    assert info.session_name == "m01__20260101_120000__ephys"
    assert info.backend == "openephys"
    assert info.extra == {}


def test_setup_config_has_no_host_session_field():
    cfg = SetupConfig(name="rig1")
    assert not hasattr(cfg, "host_session")


# ---------------------------------------------------------------------------
# make_host_session factory: entry-point driven


def test_make_host_session_openephys(monkeypatch):
    from murineshiftwork.hardware.host_session import make_host_session

    ep = MagicMock()
    ep.name = "openephys"
    ep.load.return_value = OpenEphysHostSession
    monkeypatch.setattr(
        "murineshiftwork.hardware.host_session.entry_points",
        lambda group: [ep],
    )
    client = make_host_session("openephys", url="127.0.0.1")
    assert isinstance(client, OpenEphysHostSession)
    assert isinstance(client, HostSessionProtocol)


def test_make_host_session_unknown_type_raises(monkeypatch):
    from murineshiftwork.hardware.host_session import make_host_session

    monkeypatch.setattr(
        "murineshiftwork.hardware.host_session.entry_points",
        lambda group: [],
    )
    with pytest.raises(ValueError, match="No msw.host plugin"):
        make_host_session("imaging", url="127.0.0.1")


def test_make_host_session_normalises_name(monkeypatch):
    from murineshiftwork.hardware.host_session import make_host_session

    ep = MagicMock()
    ep.name = "openephys"
    ep.load.return_value = OpenEphysHostSession
    monkeypatch.setattr(
        "murineshiftwork.hardware.host_session.entry_points",
        lambda group: [ep],
    )
    client = make_host_session("open-ephys", url="127.0.0.1")
    assert isinstance(client, OpenEphysHostSession)


# ---------------------------------------------------------------------------
# OpenEphysHostSession.attach: mocked HTTP


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


def _attach_with_mock_gui(client, gui_mock):
    with patch.dict(
        "sys.modules",
        {
            "msw_open_ephys": MagicMock(),
            "msw_open_ephys.controller": MagicMock(OEController=lambda ip: gui_mock),
        },
    ):
        return client.attach()


def test_attach_returns_none_on_connection_error():
    gui = MagicMock()
    type(gui).status = PropertyMock(side_effect=Exception("Connection refused"))
    client = OpenEphysHostSession(url="127.0.0.1")
    assert _attach_with_mock_gui(client, gui) is None


def test_attach_valid_three_part_base_text():
    gui = _make_gui_mock(
        status="RECORD",
        base_text="m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi",
        record_nodes=[{"parent_directory": "/data/rig1"}],
    )
    client = OpenEphysHostSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.session_name == "m01__20260101_120000__ephys"
    assert info.subject == "m01"
    assert info.parent_directory == "/data/rig1"
    assert info.backend == "openephys"
    assert info.extra["oe_session_name"] == "m01__20260101_120000__pxi"


def test_attach_two_part_base_text_still_works():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260101_120000__ephys",
    )
    client = OpenEphysHostSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.session_name == "m01__20260101_120000__ephys"
    assert info.extra["oe_session_name"] == ""


def test_attach_one_part_base_text_returns_none():
    gui = _make_gui_mock(status="IDLE", base_text="YYYY-MM-DD_HH-MM-SS")
    client = OpenEphysHostSession(url="127.0.0.1")
    assert _attach_with_mock_gui(client, gui) is None


def test_attach_empty_base_text_returns_none():
    gui = _make_gui_mock(status="IDLE", base_text="")
    client = OpenEphysHostSession(url="127.0.0.1")
    assert _attach_with_mock_gui(client, gui) is None


def test_attach_require_recording_blocks_idle():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi",
    )
    client = OpenEphysHostSession(url="127.0.0.1", require_recording=True)
    assert _attach_with_mock_gui(client, gui) is None


def test_attach_require_recording_passes_when_recording():
    gui = _make_gui_mock(
        status="RECORD",
        base_text="m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi",
    )
    client = OpenEphysHostSession(url="127.0.0.1", require_recording=True)
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.session_name == "m01__20260101_120000__ephys"


def test_attach_host_parsed_from_url():
    client = OpenEphysHostSession(url="http://10.0.10.111:37497")
    assert client._host == "10.0.10.111"


def test_start_and_stop_are_noops():
    client = OpenEphysHostSession(url="127.0.0.1")
    client.start()
    client.stop()


# ---------------------------------------------------------------------------
# base_text parsing invariants


def test_attach_second_precision_datetime():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260524_143022__ephys/m01__20260524_143022__pxi",
    )
    client = OpenEphysHostSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.session_name == "m01__20260524_143022__ephys"


def test_attach_microsecond_precision_datetime():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/m01__20260524_143022_123456__ephys/m01__20260524_143022_123456__pxi",
    )
    client = OpenEphysHostSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.session_name == "m01__20260524_143022_123456__ephys"


def test_attach_leading_trailing_slashes_stripped():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="/m01/m01__20260101_120000__ephys/m01__20260101_120000__pxi/",
    )
    client = OpenEphysHostSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None
    assert info.session_name == "m01__20260101_120000__ephys"


def test_attach_invalid_acq_segment_returns_none():
    gui = _make_gui_mock(
        status="IDLE",
        base_text="m01/YYYY-MM-DD_HH-MM-SS/something",
    )
    client = OpenEphysHostSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is None
    assert "not a valid MSW session name" in client.fail_reason


def test_attach_acquisition_and_session_levels_are_distinct_in_v42():
    # v4.2 deliberately differentiates the two levels: the acquisition carries
    # acq_type + optional version, the session container carries session_type.
    from murineshiftwork.namespace.paths import get_msw_builder

    b = get_msw_builder()
    acq_spec = b.spec.levels["acquisition"]
    ses_spec = b.spec.levels["session"]
    assert acq_spec.template != ses_spec.template
    assert "acq_type" in acq_spec.template
    assert "session_type" in ses_spec.template


# ---------------------------------------------------------------------------
# Integration: base_text -> session_name -> generate_session_paths


def test_attach_feeds_generate_session_paths_correctly(tmp_path):
    from murineshiftwork.namespace.paths import generate_session_paths

    gui = _make_gui_mock(
        status="RECORD",
        base_text="m01/m01__20260524_143022__ephys/m01__20260524_143022__pxi",
        record_nodes=[{"parent_directory": "/data/rig1"}],
    )
    client = OpenEphysHostSession(url="127.0.0.1")
    info = _attach_with_mock_gui(client, gui)
    assert info is not None

    paths = generate_session_paths(
        subject="m01",
        task="sequence",
        acq_type="sequence",
        basepath=tmp_path,
        linked_to=info.session_name,
        printout=False,
    )

    rel_parts = Path(paths["session_folder_relative"]).parts
    assert rel_parts[0] == "m01"
    assert rel_parts[1] == "m01__20260524_143022__ephys"  # host session dir
    assert rel_parts[2].startswith("m01__")  # MSW acquisition dir
    # v4.2: acquisition dir carries acq_type + default version suffix.
    assert "__sequence" in rel_parts[2]
    assert rel_parts[2].endswith("__v1")
    assert paths["host_session_name"] == "m01__20260524_143022__ephys"
    assert paths["acquisition_name"] == paths["session_basename"]
