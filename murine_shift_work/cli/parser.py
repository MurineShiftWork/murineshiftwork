from argparse import ArgumentDefaultsHelpFormatter
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from textwrap import dedent

from murine_shift_work import __version__
from murine_shift_work.cli.evaluate import available_tasks
from murine_shift_work.cli.evaluate import default_config_dir
from murine_shift_work.cli.evaluate import default_out_path
from murine_shift_work.cli.execute import run_register
from murine_shift_work.cli.execute import run_task
from murine_shift_work.logic.log import get_default_log_file_path


class ArgparseFormatter(
    ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter
):
    pass


def add_args_for_general_use(parser=None):
    general_args = parser.add_argument_group("General arguments")
    general_args.add_argument(
        "-s",
        "--subject",
        type=str,
        default="_test_subject",
        help="Subject name",
    )
    general_args.add_argument(
        "-t",
        "--task",
        type=str,
        default="",
        help="Task name or unique part of task name",
    )
    general_args.add_argument(
        "-o",
        "--out-path",
        type=str,
        default=default_out_path,
        help="Out path for task data",
    )
    general_args.add_argument(
        "-child-to",
        "--is-child-session-to",
        dest="is_child_session_to",
        type=str,
        default="",
        help="Set if is child session. If not empty, skips subject dir & saves session dir directly in `--out-path`",
    )
    metadata_group = parser.add_argument_group("Metadata")
    metadata_group.add_argument(
        "-meta",
        "--metadata",
        metavar="KEY=VALUE",
        nargs="+",
        dest="metadata_list",
        help="Metadata key-value pairs. Use other named metadata fields or specify any relevant key-value pair",
    )
    metadata_group.add_argument(
        "--researcher",
        type=str,
        default="unknown_researcher",
        help="Name or initials of researcher acquiring the data",
    )
    metadata_group.add_argument(
        "--setup",
        type=str,
        default="unknown_setup",
        help="Name or ID of setup",
    )
    metadata_group.add_argument(
        "--experiment",
        type=str,
        default="unknown_experiment",
        help="Name or ID of experiment",
    )
    config_arg_group = parser.add_argument_group(
        "Configuration & settings files"
    )
    config_arg_group.add_argument(
        "-cd",
        "--config-dir",
        type=str,
        default=default_config_dir,
        help="Directory that contains config files. Used if specific config files are only names, not full paths.",
    )
    config_arg_group.add_argument(
        "-cs",
        "--config-file-subjects",
        type=str,
        default="subject.settings",
        help="Settings file name or path.",
    )
    config_arg_group.add_argument(
        "-ct",
        "--config-file-task",
        type=str,
        default="task.settings",
        help="Settings file name or path.",
    )
    config_arg_group.add_argument(
        "-cc",
        "--config-file-camera",
        type=str,
        default="camera.rcc.config",
        help="Settings file name or path. (Only relevant for `run`)",
    )
    return general_args


def add_args_for_hardware_and_calibration(parser=None):
    hardware_args = parser.add_argument_group("Hardware settings")
    hardware_args.add_argument(
        "-b",
        "--serial-port-bpod",
        type=str,
        default="/dev/ttyACM0",
        help="Serial port for bpod. Unix: /dev/ttyACM{no}. Windows: COM{no}.",
    )
    hardware_args.add_argument(
        "-p",
        "--serial-port-pulsepal",
        type=str,
        default="/dev/ttyACM1",
        help="Serial port for pulsepal. Unix: /dev/ttyACM{no}. Windows: COM{no}.",
    )
    hardware_args.add_argument(
        "-scale",
        "--serial-port-scale",
        dest="serial_port_scale",
        type=str,
        default="/dev/ttyACM2",
        help="Serial port for weighing scale (for calibration). Unix: /dev/ttyACM{no}. Windows: COM{no}.",
    )
    hardware_args.add_argument(
        "-stage",
        "--serial-port-stage",
        dest="serial_port_stage",
        type=str,
        default="/dev/ttyUSB0",
        help="Serial port for stage controller (e.g. for moving spouts). Unix: /dev/ttyACM{no}. Windows: COM{no}.",
    )
    calibration_arg_group = parser.add_argument_group("Calibration files")
    calibration_arg_group.add_argument(
        "-cwater",
        "--calibration-file-water",
        dest="calibration_file_water",
        type=str,
        default="calibration.water.default.csv",
        help="Default water calibration file (Only relevant for `run`)",
    )
    calibration_arg_group.add_argument(
        "-csound",
        "--calibration-file-sound",
        dest="calibration_file_sound",
        type=str,
        default="calibration.sound.default.csv",
        help="Default sound calibration file (Only relevant for `run`)",
    )
    return hardware_args


def add_args_for_flow_control(parser=None):
    flow_control_options = parser.add_argument_group("Development options.")
    flow_control_options.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        type=str,
        default="INFO",
        help="Log level, e.g. 'INFO' or 'DEBUG'",
    )
    flow_control_options.add_argument(
        "-lf",
        "--log-file",
        dest="log_file",
        type=str,
        default=get_default_log_file_path(),
        help="Log file path. Filenames are ignored",
    )
    flow_control_options.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Sets log level to DEBUG and enables additional development features",
    )
    return flow_control_options


def make_subparser_register(sub_parsers):
    description = "Register subjects"
    examples = dedent(
        f"""Examples:

    msw register subject [optional: task]

    msw register add _test_subject
    msw register add _test_subject probabilistic_switching
    msw register add _test_subject -t/--task probabilistic_switching
    msw register remove _test_subject
    msw register remove _test_subject --task probabilistic_switching
    msw register rename

Available tasks:
{available_tasks}

    """
    )
    parser_for_register = sub_parsers.add_parser(
        name="register",
        description=description,
        help=description,
        epilog=examples,
        formatter_class=ArgparseFormatter,
    )
    parser_for_register.add_argument(
        "subcommand",
        type=str,
        choices=["add", "remove", "rename"],
        help="Choose from: add, remove, rename",
    )
    add_args_for_general_use(parser_for_register)
    add_args_for_flow_control(parser_for_register)

    reg_group = parser_for_register.add_argument_group("Registration options")
    reg_group.add_argument(
        "-n",
        "--new-alias",
        dest="new_alias",
        type=str,
        default="",
        help="New alias for subject, if subcommand options are 'register move'",
    )
    reg_group.add_argument(
        "-m",
        "--move-data",
        dest="move_data",
        default=True,
        action="store_true",
        help="If subcommand is 'move', then tries to move existing acquisitions to new subject name",
    )

    parser_for_register.set_defaults(func=run_register)


def make_subparser_run(sub_parsers):
    description = "Run tasks"
    examples = dedent(
        f"""Examples:

    msw run -t task_name -s subject_name
    msw run -t task_name -s subject_name -b serial_port_bpod

Available tasks:
{available_tasks}

    """
    )
    parser_for_run = sub_parsers.add_parser(
        name="run",
        description=description,
        help=description,
        epilog=examples,
        formatter_class=ArgparseFormatter,
    )
    add_args_for_general_use(parser_for_run)
    add_args_for_hardware_and_calibration(parser_for_run)
    add_args_for_flow_control(parser_for_run)
    parser_for_run.set_defaults(func=run_task)


def parse_args(args=None):
    """Parser for Murine Shift Work.
    Assumes input is args without first argument as py file path == sys.argv with first argument removed.

    :param args: List of arguments
    :return: Dict of parsed arguments
    """
    epilog = dedent("""""")
    main_parser = ArgumentParser(
        prog="murineshiftwork",
        description="Behavior acquisition for murine tasks. "
        "Options for video acquisition with RPi Camera Colony and stimulation with PulsePal.",
        epilog=epilog,  # FIXME: add info how to use `register` and `run` subcommands
        formatter_class=ArgparseFormatter,
    )
    main_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"Murine Shift Work: {__version__}",
        help="Show the version number and exit.",
    )
    sub_parsers = main_parser.add_subparsers(metavar="command", dest="command")
    sub_parsers.required = True
    make_subparser_register(sub_parsers)
    make_subparser_run(sub_parsers)

    parsed_args = main_parser.parse_args(args=args)
    return parsed_args.__dict__
