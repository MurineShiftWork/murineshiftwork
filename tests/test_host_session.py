"""Integration tests for the host-session plugin system.

Exercises the installed ``msw-open-ephys`` plugin through msw-core's entry-point dispatch and
feeds its attach() result into msw-io's session path generation. Unit coverage lives with each
package: ``_parse_host``/``attach`` parsing in msw-open-ephys, ``make_host_session`` dispatch in
msw-core, ``HostSessionInfo`` in msw-plugin-api.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

msw_open_ephys = pytest.importorskip("msw_open_ephys")
from msw_open_ephys.host import OpenEphysHostSession  # noqa: E402
from msw_plugin_api import HostSessionProtocol  # noqa: E402

# ---------------------------------------------------------------------------
# make_host_session resolves the installed plugin through the real entry point


def test_make_host_session_resolves_installed_openephys_plugin():
    from murineshiftwork.hardware.host_session import make_host_session

    client = make_host_session("open-ephys", url="http://10.0.10.111:37497")
    assert isinstance(client, OpenEphysHostSession)
    assert isinstance(client, HostSessionProtocol)
    assert client._host == "10.0.10.111"


# ---------------------------------------------------------------------------
# base_text parsing relies on msw-io's session and acquisition levels


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
# (attach() runs against a mocked OE HTTP controller)


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
