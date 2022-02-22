import argparse
import os

# DEFAULT_REMOTE_IP = "172.24.242.233"  # FIXME: ip seems to change all the time
DEFAULT_REMOTE_IP = "192.168.100.48"
DEFAULT_REMOTE_PORT = 5558
DEFAULT_REMOTE_PATH = r"E:\\OE_DATA\\LBR"
DEFAULT_LOCAL_PATH = os.path.expanduser("~/data")
DEFAULT_ACQUISITION_NAME = "_test_subject"
DEFAULT_ACQUISITION_TASK = "ephys_multi_behaviour"
DEFAULT_SESSION_NAME = "ephys_pxi"  # TODO: use this parameter as --session-name for Intan EMG/EEG recordings


def make_parser_remote_ephys():
    parser = argparse.ArgumentParser()
    connection_group = parser.add_argument_group("Remote")
    connection_group.add_argument(
        "-ip",
        "--remote-ip",
        dest="remote_ip",
        type=str,
        default=DEFAULT_REMOTE_IP,
        help="Remote IP address",
    )
    connection_group.add_argument(
        "-port",
        "--remote-port",
        dest="remote_port",
        type=int,
        default=DEFAULT_REMOTE_PORT,
        help="Remote port",
    )
    connection_group.add_argument(
        "-a",
        "--remote-path",
        dest="remote_path",
        type=str,
        default=DEFAULT_REMOTE_PATH,
        help="Remote acquisition path",
    )
    connection_group.add_argument(
        "-l",
        "--local-path",
        dest="local_path",
        type=str,
        default=DEFAULT_LOCAL_PATH,
        help="Remote acquisition path",
    )
    connection_group.add_argument(
        "-n",
        "--acquisition-name",
        dest="acquisition_name",
        type=str,
        default=DEFAULT_ACQUISITION_NAME,
        help=f"Acquisition name. For example: {DEFAULT_ACQUISITION_NAME}",
    )
    connection_group.add_argument(
        "-t",
        "--acquisition-task",
        dest="acquisition_task",
        type=str,
        default=DEFAULT_ACQUISITION_TASK,
        help=f"Acquisition task. Default: {DEFAULT_ACQUISITION_TASK}",
    )
    connection_group.add_argument(
        "-s",
        "--session-name",
        dest="session_name",
        type=str,
        default=DEFAULT_SESSION_NAME,
        help=f"Acquisition task. Default: {DEFAULT_SESSION_NAME}",
    )
    action_group = parser.add_argument_group("Actions")
    action_group.add_argument(
        "--status",
        dest="status",
        action="store_true",
        default=False,
        help="Get status",
    )

    action_group.add_argument(
        "--preview",
        dest="preview",
        action="store_true",
        default=False,
        help="Toggle preview",
    )
    action_group.add_argument(
        "--record",
        dest="record",
        action="store_true",
        default=False,
        help="Toggle recording",
    )
    action_group.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Sets log level to DEBUG and enables additional development features",
    )
    return parser
