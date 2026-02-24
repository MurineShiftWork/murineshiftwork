import logging
import os
import sys
import time

from murine_shift_work.logic.log import setup_logging
from murine_shift_work.remote_ephys.cli import make_parser_remote_ephys
from murine_shift_work.remote_ephys.controller import RemoteOpenEphysController


def _evaluate_metadata(args_dict):
    metadata_list = args_dict.get("metadata_list", None)
    if metadata_list is not None:
        metadata_list = [
            v.strip(" ").strip("'").strip('"')
            for v in metadata_list
            if "=" in v
        ]
        metadata_dict = dict(map(lambda s: s.split("="), metadata_list))
        #
        # for metadata_key in ["researcher", "setup", "experiment"]:
        #     if (
        #         not args_dict[metadata_key].startswith("unknown_")
        #         or metadata_key not in metadata_dict
        #     ):
        #         # metadata_dict[f"_original__{metadata_key}"] = metadata_dict[metadata_key]
        #         print(metadata_key)
        #         metadata_dict[metadata_key] = args_dict[metadata_key]

        args_dict["metadata"] = metadata_dict
    return args_dict


def run_remote_ephys():
    setup_logging()

    parser = make_parser_remote_ephys()
    args = parser.parse_args()
    args_dict = args.__dict__
    args_dict = _evaluate_metadata(args_dict=args_dict)

    if not (args.status or args.preview or args.record):
        logging.info(
            f"No action requested: Status: {args.status} | Preview: {args.preview} | Record: {args.record}"
        )
        sys.exit(0)

    ctrl = RemoteOpenEphysController(**args_dict)

    if args.status:
        logging.info("Status requested")

        logging.info(f"Is previewing: {ctrl.is_previewing()}")
        logging.info(f"Is recording: {ctrl.is_previewing()}")
        logging.info(f"Recording path: {ctrl.get_recording_path()}")

    elif args.preview:
        logging.info("Preview toggle")
        if ctrl.is_previewing():
            ctrl.stop_preview()
        else:
            ctrl.start_preview()

    elif args.record:
        logging.info("Recording toggle")
        if ctrl.is_recording():
            ctrl.stop_recording()
            # Safety feature to safeguard against later acquisitions on top of this path in RecordNode:
            ctrl.safeguard_path_by_overwrite()
        else:
            ctrl.start_recording()

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


if __name__ == "__main__":
    # import sys
    sys.argv += ["--record"]  #  "--is-child-session-to", "ch-sess"
    run_remote_ephys()

    print("x")
