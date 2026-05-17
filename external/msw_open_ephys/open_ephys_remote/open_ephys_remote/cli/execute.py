import json
import logging
import time
from datetime import datetime
from pathlib import Path
from pprint import pprint

from open_ephys_remote.cli._log import setup_logging
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
    port=37497,
    subject="_test_subject",
    local_path="/mnt/fastdata/data",
    remote_path="/mnt/fastdata/data",
    acquisition_extension="ephys_multi_behavior",
    session_extension="",
    is_child_session_to="",
    **kwargs,
):
    """
    Expect variables:
    - is_child_session_to:  "subject/acquisition_name"
    make paths
    - cases:
      - npx master that cannot create sub-dir via web api
      - intan ttl that is sub session to npx master
      - intan ttl that is master session itself

    :param ip:
    :param port:
    :param subject:
    :param local_path:
    :param remote_path:
    :param acquisition_extension:
    :param session_extension:
    :param is_child_session_to:
    :param kwargs:
    :return:
    """
    setup_logging(level="DEBUG" if kwargs.get("debug") else "INFO")

    assert subject
    dt = _get_date_str()
    # subject = subjePath(is_child_session_to).name.split("__")[0]
    acquisition_name = "__".join([subject, dt, acquisition_extension])
    session_name = "__".join([subject, dt, session_extension])
    acq_path = Path(subject) / acquisition_name / session_name

    remote_path = Path(remote_path)

    if is_child_session_to:
        logging.info("as CHILD session")
        local_path_full = Path(local_path) / is_child_session_to

        if ip == "localhost" and "intan" in session_extension:
            logging.info("as local/intan session")
            # subject/acquisition_name/session_name
            main_dir = Path(is_child_session_to) / session_name
            remote_path = remote_path / is_child_session_to
        else:
            ValueError(session_extension)

    else:
        logging.info("as MAIN session")
        local_path_full = Path(local_path) / subject / acquisition_name

        if "pxi" in session_extension:
            logging.info("as PXI session")
            # subject/session_name
            # -> which has the same datetime as acquisition_name, so can be auto-moved later
            main_dir = Path(subject) / session_name
            # remote_path = remote_path
        elif ip == "localhost":
            logging.info("as local session")
            # subject/acquisition_name/session_name
            main_dir = acq_path
            remote_path = remote_path / main_dir.parent
        else:
            ValueError(session_extension)

    # Settings
    # local_path_full = Path(local_path) / acq_path
    metadata_file = local_path_full / f"{session_name}.settings.ephys.json"
    main_dir = Path(main_dir).as_posix()
    remote_path = Path(remote_path).as_posix()
    settings = {
        # TODO: use version to split analysis synch of TTL from intan vs nidaq
        "version": 2,
        # Dir parts
        "subject": subject,
        "acquisition_name": subject,
        "datetime": dt,
        "full_acquisition_name": main_dir,
        "main_session_folder": main_dir,
        "full_session_name": session_name,
        "is_child_session_to": is_child_session_to,
        "acquisition_task_name": acquisition_extension,
        "session_name": session_extension,
        # Local paths
        "local_path": local_path,
        "local_path_full": local_path_full.as_posix(),
        "metadata_file": metadata_file.as_posix(),
        # Remote
        "remote_ip": ip,
        "remote_port": port,
        "remote_path": remote_path,
        "parent_directory": remote_path,
        "base_text": session_name,
        "prepend_text": "",
        "append_text": "",
        # Legacy
        "create_new_dir": True,
    }

    # Logging level
    # log_level = "DEBUG" if kwargs.get("debug", True) else "INFO"
    # setup_logging(
    #     level=log_level,
    #     log_file=local_path_full / (session_name + ".log"),
    # )

    oe = OERemoteController(
        ip=ip,
        port=port,
        **kwargs,
    )
    oe.preview()

    pprint(oe.settings)

    if kwargs.get("func"):
        kwargs.pop("func")

    _ = oe.set_settings(settings=settings)
    _ = oe.set_all_record_nodes(settings=settings)
    pprint(oe.settings)
    time.sleep(1)

    oe.record()

    time.sleep(1)

    if oe.status == oe._status_record:
        Path(local_path_full).mkdir(parents=True, exist_ok=True)
        (Path(local_path_full) / session_name).mkdir(parents=True, exist_ok=True)

        with open(metadata_file, "w") as f:
            settings["oe_settings"] = oe.settings
            out_json = json.dumps(settings, indent=4, sort_keys=True)
            f.write(out_json)
            logging.debug(f"Metadata written to: {metadata_file}")
            logging.info(out_json)

    logging.info(f"Settings: {json.dumps(settings, indent=4, sort_keys=True)}")
    logging.info(f"Acquisition name:  {acquisition_name}")
    logging.info(f"Session name:  {session_name}")
    logging.info(f"Children are:  {(Path(subject) / acquisition_name).as_posix()}")
    if settings["is_child_session_to"]:
        logging.info(f"Is child session to:  {Path(is_child_session_to).as_posix()} ")


def run_stop(ip=None, port=37497, **kwargs):
    oe = OERemoteController(ip=ip, port=port, **kwargs)
    oe.stop()
