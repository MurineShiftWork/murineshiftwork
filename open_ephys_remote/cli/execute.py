import logging
from datetime import datetime
from pathlib import Path
from pprint import pprint

from open_ephys_remote.controller import OERemoteController


def _get_date_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_status(ip=None, port=None, **kwargs):
    oe = OERemoteController(ip=ip, port=port, **kwargs)
    logging.info(f"OE remote status: {oe.status}")


def run_preview(ip=None, port=None, **kwargs):
    oe = OERemoteController(ip=ip, port=port, **kwargs)
    oe.preview()


def run_record(
    ip=None,
    port=None,
    prepend_text=None,
    base_text=None,
    append_text=None,
    parent_directory=None,
    **kwargs,
):
    # ip = "192.168.100.240"
    dt = _get_date_str()
    subject = "_test_oe"

    main_session_folder = "__".join([subject, dt, "ephys_multi_behavior"])
    session_name = "__".join([subject, dt, "ephys_pxi"])

    local_path = Path("/mnt/fastdata/data")

    local_path_full = (
        Path(local_path) / subject / main_session_folder / session_name
    )
    local_path_full.mkdir(parents=True, exist_ok=True)

    metadata_file = local_path_full / f"{session_name}.settings.ephys.json"

    local_path_full = str(local_path_full)
    metadata_file = str(metadata_file)

    settings = {
        "append_text": "",
        "base_text": f"{session_name}",
        "prepend_text": "",
        # "parent_directory": f"E:\\\\OE_DATA\\\\LBR\\\\{subject}\\\\{main_session_folder}",  # main_session_folder
        # "parent_directory": f"E:\\\\OE_DATA\\\\LBR\\\\{main_session_folder}",  # main_session_folder
        "parent_directory": f"/home/lbr/data/{main_session_folder}",  # main_session_folder
    }

    oe = OERemoteController(
        ip=ip,
        port=port,
        prepend_text=prepend_text,
        base_text=base_text,
        append_text=append_text,
        parent_directory=parent_directory,
        **kwargs,
    )
    pprint(oe.settings)

    kwargs.pop("func")
    settings = oe.set_settings(settings=kwargs)
    pprint(settings)

    oe.record()

    if oe.status == oe._status_record:
        pass  # fixme: SAVE metadata file locally


def run_stop(ip=None, port=None, **kwargs):
    oe = OERemoteController(ip=ip, port=port, **kwargs)
    oe.stop()
