import json
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
    def _create_namespace_settings(kwargs: dict = None):
        # Base vars
        subject = kwargs["subject"]
        is_child_session_to = kwargs.get("is_child_session_to")
        dt = _get_date_str()

        acquisition_extension = kwargs["acquisition_extension"]
        session_extension = kwargs["session_extension"]

        if is_child_session_to:
            subject = is_child_session_to.split("__")[0]
            main_session_folder = is_child_session_to
        else:
            main_session_folder = "__".join(
                [subject, dt, acquisition_extension]
            )

        session_name = "__".join([subject, dt, session_extension])

        # Local file
        local_path_full = (
            Path(kwargs["local_path"])
            / subject
            / main_session_folder
            / session_name
        )

        metadata_file = local_path_full / f"{session_name}.settings.ephys.json"

        local_path_full = str(local_path_full)
        metadata_file = str(metadata_file)
        remote_path = Path(kwargs["remote_path"])

        # Settings
        settings = {
            "acquisition_name": subject,
            "acquisition_task_name": acquisition_extension,
            "create_new_dir": True,
            "datetime": dt,
            "full_acquisition_name": main_session_folder,
            "full_session_name": session_name,
            #
            "is_child_session_to": is_child_session_to,
            "local_path": kwargs["local_path"],
            "local_path_full": str(local_path_full),
            "metadata_file": str(metadata_file),
            "remote_ip": ip,
            "remote_path": remote_path.as_posix(),
            "parent_directory": remote_path.as_posix(),
            "base_text": f"{session_name}",
            "remote_port": port,
            "session_name": session_extension,
            "subject": subject,
        }
        return settings

    settings = _create_namespace_settings(kwargs=kwargs)
    Path(settings["local_path_full"]).mkdir(parents=True, exist_ok=True)

    oe = OERemoteController(
        ip=ip,
        port=port,
        base_text=base_text,
        parent_directory=parent_directory,
        **kwargs,
    )
    pprint(oe.settings)

    kwargs.pop("func")
    _ = oe.set_settings(settings=settings)
    _ = oe.set_all_record_nodes(settings=settings)
    pprint(oe.settings)

    oe.record()

    if oe.status == oe._status_record:
        metadata_file = settings["metadata_file"]
        with open(metadata_file, "w") as f:
            settings["oe_settings"] = oe.settings
            out_json = json.dumps(settings, indent=4, sort_keys=True)
            f.write(out_json)
            logging.debug(f"Metadata written to: {metadata_file}")
            logging.info(out_json)

    logging.info(f"Settings: {json.dumps(settings, indent=4, sort_keys=True)}")
    logging.info(f"Acquisition name:  {settings.get('main_session_folder')}")
    logging.info(f"Session name:  {settings.get('full_session_name')}")
    if settings["is_child_session_to"]:
        logging.info(
            f"Is child session to:  {settings.get('is_child_session_to')} "
        )


def run_stop(ip=None, port=None, **kwargs):
    oe = OERemoteController(ip=ip, port=port, **kwargs)
    oe.stop()
