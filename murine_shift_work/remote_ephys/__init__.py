import logging
import os
import sys
import time

from murine_shift_work.logic.log import setup_logging
from murine_shift_work.remote_ephys.cli import make_parser_remote_ephys
from murine_shift_work.remote_ephys.controller import RemoteOpenEphysController


def run_remote_ephys():
    setup_logging()

    parser = make_parser_remote_ephys()
    args = parser.parse_args()

    if not (args.status or args.preview or args.record):
        logging.info(
            f"No action requested: Status: {args.status} | Preview: {args.preview} | Record: {args.record}"
        )
        sys.exit(0)

    ctrl = RemoteOpenEphysController(**args.__dict__)

    if args.status:
        logging.info("Status requested")

        logging.info(f"Is previewing: {ctrl.is_previewing()}")
        logging.info(f"Is recording: {ctrl.is_previewing()}")
        logging.info(f"Recording path: {ctrl.get_recording_path()}")

    elif args.status:
        logging.info("Preview toggle")
        if ctrl.is_previewing():
            ctrl.stop_preview()
        else:
            ctrl.start_preview()

    elif args.status:
        logging.info("Recording toggle")
        if ctrl.is_recording():
            ctrl.stop_recording()
        else:
            ctrl.start_recording()

    else:
        sys.exit(0)


def test_controller():
    """Test: Controller object directly."""
    ctrl = RemoteOpenEphysController(
        remote_ip="172.24.242.219",
        # remote_ip="192.168.100.48",
        remote_port=5558,
        remote_path=r"E:\\OE_DATA\\LBR\\",
        acquisition_name="_test_subject",
        local_path=os.path.expanduser("~/data"),
    )

    ctrl.start_preview()
    time.sleep(5)
    ctrl.stop_preview()


def test_status():
    """Test: CLI for status request."""
    import sys

    sys.argv += ["--status"]
    run_remote_ephys()


def test_preview():
    """Test: CLI for preview request."""
    import sys

    sys.argv += ["--preview"]
    run_remote_ephys()


def test_record():
    """Test: CLI for record request."""
    import sys

    sys.argv += ["--record"]
    run_remote_ephys()
