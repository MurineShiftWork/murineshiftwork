import json
import logging
import time
from pathlib import Path

from rich import get_console
from rich.logging import RichHandler

from oe_remote.controller import OEController
from oe_remote.session import Session


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(debug: bool = False) -> None:
    level = "DEBUG" if debug else "INFO"
    logger = logging.getLogger()
    if logger.handlers:
        return
    logger.setLevel(getattr(logging, level))
    handler = RichHandler(
        console=get_console(),
        level=level,
        enable_link_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(ip: str, port: int, debug: bool = False, **_) -> None:
    setup_logging(debug)
    oe = OEController(ip=ip, port=port)
    logging.info(f"Open Ephys status: {oe.status}")


def cmd_preview(ip: str, port: int, debug: bool = False, **_) -> None:
    setup_logging(debug)
    oe = OEController(ip=ip, port=port)
    oe.preview()
    logging.info(f"Open Ephys status: {oe.status}")


def cmd_stop(ip: str, port: int, debug: bool = False, **_) -> None:
    setup_logging(debug)
    oe = OEController(ip=ip, port=port)
    oe.stop()
    logging.info(f"Open Ephys status: {oe.status}")


def cmd_record(
    ip: str,
    port: int,
    subject: str,
    local_path: str,
    remote_path: str,
    session_extension: str,
    acquisition_extension: str = "",
    is_child_session_to: str = "",
    debug: bool = False,
    **_,
) -> None:
    setup_logging(debug)

    is_child_session_to = Session.resolve_child(is_child_session_to)

    session = Session(
        subject=subject,
        session_extension=session_extension,
        acquisition_extension=acquisition_extension,
        local_path=local_path,
        remote_path=remote_path,
        ip=ip,
        port=port,
        is_child_session_to=is_child_session_to,
    )

    logging.info(f"Session:      {session.session_name}")
    if session.acquisition_extension:
        logging.info(f"Acquisition:  {session.acquisition_name}")
    logging.info(f"Records to:   {session.main_session_folder}")
    logging.info(f"Local path:   {session.local_path_full}")
    logging.debug(f"parent_directory: {session.parent_directory}")
    logging.debug(f"base_text:        {session.base_text}")

    oe = OEController(ip=ip, port=port)
    oe.preview()

    oe.configure_recording(session.parent_directory, session.base_text)
    logging.debug(f"Recording confirmed: {oe.recording}")

    time.sleep(1)
    oe.record()
    time.sleep(1)

    if oe.status != OEController.MODE_RECORD:
        logging.error("Open Ephys did not enter RECORD mode — aborting metadata write.")
        return

    # Create local directories and write metadata
    session.local_path_full.mkdir(parents=True, exist_ok=True)
    (session.local_path_full / session.session_name).mkdir(parents=True, exist_ok=True)

    meta = session.metadata(oe_state=oe.recording)
    with open(session.metadata_file, "w") as f:
        json.dump(meta, f, indent=4, sort_keys=True)
    logging.info(f"Metadata:     {session.metadata_file}")

    # Always cache so --child @last works after any record command
    session.save_to_cache()
    print(f"\nSESSION PATH (use with --child for further sessions):")
    print(f"  {session._cache_path}\n")
