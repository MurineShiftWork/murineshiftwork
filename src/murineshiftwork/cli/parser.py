from argparse import ArgumentDefaultsHelpFormatter
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from importlib.metadata import version as _get_version
from textwrap import dedent

from murineshiftwork.cli.defaults import available_tasks
from murineshiftwork.cli.defaults import default_config_dir
from murineshiftwork.cli.defaults import default_out_path
from murineshiftwork.cli.execute import run_action
from murineshiftwork.cli.execute import run_calibration
from murineshiftwork.cli.execute import run_init
from murineshiftwork.cli.execute import run_register
from murineshiftwork.cli.execute import run_setup
from murineshiftwork.cli.execute import run_subject
from murineshiftwork.cli.execute import run_task

try:
    _MSW_VERSION = _get_version("murineshiftwork")
except Exception:
    _MSW_VERSION = "unknown"


class ArgparseFormatter(
    ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter
):
    pass


def _add_session_args(parser):
    g = parser.add_argument_group("Session")
    g.add_argument(
        "-s",
        "--subject",
        type=str,
        default="_test_subject",
        help="Subject name",
    )
    g.add_argument(
        "-t",
        "--task",
        type=str,
        default="",
        help="Task name or unique substring of task name",
    )
    g.add_argument(
        "-o",
        "--out-path",
        type=str,
        default=default_out_path,
        dest="out_path",
        help="Output directory for session data",
    )
    g.add_argument(
        "--child-of",
        "--is-child-session-to",
        dest="is_child_session_to",
        type=str,
        default="",
        help="Parent session basename; when set, saves session directly in --out-path (skips subject dir)",
    )


def _add_config_args(parser):
    g = parser.add_argument_group("Configuration")
    g.add_argument(
        "-cd",
        "--config-dir",
        type=str,
        default=default_config_dir,
        dest="config_dir",
        help="Shared config directory containing setups/, subjects/, tasks/",
    )
    g.add_argument(
        "-ct",
        "--config-file-task",
        type=str,
        default="task.yaml",
        dest="config_file_task",
        help="Task settings file name or path",
    )
    g.add_argument(
        "-cc",
        "--config-file-camera",
        type=str,
        default="camera.rcc.config",
        dest="config_file_camera",
        help="Camera settings file name or path",
    )


def _add_hardware_args(parser):
    g = parser.add_argument_group("Hardware")
    g.add_argument(
        "-b",
        "--port-bpod",
        type=str,
        default="/dev/ttyACM0",
        dest="serial_port_bpod",
        help="Serial port for Bpod (Unix: /dev/ttyACM{n}, Windows: COM{n})",
    )
    g.add_argument(
        "-p",
        "--port-pulsepal",
        type=str,
        default="/dev/ttyACM1",
        dest="serial_port_pulsepal",
        help="Serial port for PulsePal",
    )
    g.add_argument(
        "--port-scale",
        type=str,
        default="/dev/ttyACM2",
        dest="serial_port_scale",
        help="Serial port for weighing scale (calibration tasks only)",
    )
    g.add_argument(
        "--port-stage",
        type=str,
        default="/dev/ttyUSB0",
        dest="serial_port_stage",
        help="Serial port for stage controller",
    )


def _add_task_mode_args(parser):
    g = parser.add_argument_group("Task mode")
    g.add_argument(
        "--task-mode",
        dest="task_mode",
        type=str,
        default="",
        help=(
            "Named preset from task.yaml 'mode:' section. "
            "Overrides task defaults; overridden by subject YAML and -ts. "
            "Example: --task-mode probe"
        ),
    )
    g.add_argument(
        "-ts",
        "--task-settings",
        metavar="KEY=VALUE",
        nargs="+",
        dest="task_settings_overrides",
        default=[],
        help=(
            "Task-settings key-value overrides (highest priority). "
            "Example: -ts reward_amount_ul=3 n_max_trials=200"
        ),
    )


def _add_meta_args(parser):
    g = parser.add_argument_group("Metadata")
    g.add_argument(
        "--setup",
        type=str,
        default="",
        help="Setup name (must match a YAML in the setups config directory)",
    )
    g.add_argument(
        "-m",
        "--meta",
        metavar="KEY=VALUE",
        nargs="+",
        dest="metadata_list",
        help="Arbitrary metadata key-value pairs. Example: -m project=myproject cohort=1",
    )
    g.add_argument(
        "--meta-experimenter",
        type=str,
        default="",
        dest="experimenter",
        help="Experimenter name or initials (convenience shorthand for -m experimenter=NAME)",
    )


def _add_dev_args(parser):
    g = parser.add_argument_group("Development")
    g.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        type=str,
        default="INFO",
        help="Log level (INFO, DEBUG, WARNING, …)",
    )
    g.add_argument(
        "-lf",
        "--log-file",
        dest="log_file",
        type=str,
        default="",
        help="Override central log file path (default: auto-rotated in ~/.murineshiftwork/logs/)",
    )
    g.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Enable debug mode (sets log level to DEBUG, relaxes hardware checks)",
    )


def make_subparser_init(sub_parsers):
    p = sub_parsers.add_parser(
        "init",
        help="Initialise MSW on this machine (writes ~/.murineshiftwork/msw_machine.yaml)",
        formatter_class=ArgparseFormatter,
    )
    p.add_argument(
        "config_dir",
        type=str,
        help="Path to the shared msw_configs directory (created if absent)",
    )
    p.add_argument(
        "--data-dir",
        type=str,
        default="",
        dest="data_dir",
        help="Default output directory for session data (saved in msw_machine.yaml)",
    )
    p.add_argument("--force", action="store_true", default=False)
    p.set_defaults(func=run_init)


def make_subparser_setup(sub_parsers):
    p = sub_parsers.add_parser(
        "setup",
        help="Manage setup config files",
        formatter_class=ArgparseFormatter,
    )
    p.add_argument(
        "subcommand",
        choices=["create", "list"],
        help="create: make a new skeleton YAML; list: show available setups",
    )
    p.add_argument(
        "setup_name",
        nargs="?",
        default="",
        help="Setup name (required for create)",
    )
    p.add_argument(
        "-cd", "--config-dir", type=str, default="", dest="config_dir"
    )
    p.add_argument(
        "-f",
        "--filter",
        type=str,
        default="",
        dest="filter",
        help="Filter by partial name match (case-insensitive, list only)",
    )
    p.add_argument("--force", action="store_true", default=False)
    p.set_defaults(func=run_setup)


def make_subparser_subject(sub_parsers):
    p = sub_parsers.add_parser(
        "subject",
        help="Manage subject YAML config files",
        formatter_class=ArgparseFormatter,
    )
    p.add_argument(
        "subcommand",
        choices=["add", "list", "rename", "remove"],
        help="add / list / rename / remove",
    )
    p.add_argument(
        "-s",
        "--subject",
        type=str,
        default="",
        dest="subject",
        help="Subject name",
    )
    p.add_argument(
        "--new-name",
        type=str,
        default="",
        dest="new_name",
        help="New name (required for rename)",
    )
    p.add_argument("--project", type=str, default="")
    p.add_argument("--experiment", type=str, default="")
    p.add_argument("--comment", type=str, default="")
    p.add_argument(
        "-cd", "--config-dir", type=str, default="", dest="config_dir"
    )
    p.add_argument(
        "-f",
        "--filter",
        type=str,
        default="",
        dest="filter",
        help="Filter by partial name match (case-insensitive, list only)",
    )
    p.add_argument("--force", action="store_true", default=False)
    p.set_defaults(func=run_subject)


def make_subparser_run(sub_parsers):
    examples = dedent(
        f"""Examples:
    msw run -t task_name -s subject_name
    msw run -t task_name -s subject_name -b /dev/ttyACM0 --setup setup-1

Available tasks:
{available_tasks}

    """
    )
    p = sub_parsers.add_parser(
        "run",
        description="Run a behavioural task.",
        help="Run a task",
        epilog=examples,
        formatter_class=ArgparseFormatter,
    )
    _add_session_args(p)
    _add_config_args(p)
    _add_task_mode_args(p)
    _add_hardware_args(p)
    _add_meta_args(p)
    _add_dev_args(p)
    p.set_defaults(func=run_task)


def make_subparser_calibration(sub_parsers):
    p = sub_parsers.add_parser(
        "calibration",
        help="Calibration utilities (plot, inspect)",
        formatter_class=ArgparseFormatter,
    )
    p.add_argument(
        "action",
        choices=["plot"],
        help="plot: save valve calibration curves as PDF",
    )
    p.add_argument(
        "--setup",
        type=str,
        default="",
        help="Setup name to plot (plots all setups if omitted)",
    )
    p.add_argument(
        "--out",
        dest="output_dir",
        type=str,
        default=".",
        help="Output directory for PDF files",
    )
    p.add_argument(
        "-cd",
        "--config-dir",
        dest="config_dir",
        type=str,
        default="",
        help="Config directory (default: from machine config)",
    )
    p.set_defaults(func=run_calibration)


def make_subparser_action(sub_parsers):
    p = sub_parsers.add_parser(
        "action",
        help="Trigger a one-shot hardware action (valve pulse, LED flash, etc.)",
        formatter_class=ArgparseFormatter,
        description=dedent(
            """\
            Execute a discrete hardware action on a named setup device.

            Phase 1 (current): opens a fresh exclusive connection — do NOT run while a
            task session is active on the same hardware.

            Examples:
              msw action --setup setup-1 bpod valve_pulse valve_id=1 duration_s=0.025
              msw action --setup setup-1 bpod valve_pulse valve_id=1 n_pulses=5 duration_s=0.05
              msw action --setup setup-1 bpod valve_flush valve_id=3
            """
        ),
    )
    p.add_argument(
        "--setup",
        type=str,
        required=True,
        help="Setup name (must match a YAML in the setups config directory)",
    )
    p.add_argument(
        "-cd",
        "--config-dir",
        type=str,
        default="",
        dest="config_dir",
        help="Config directory (default: from machine config)",
    )
    p.add_argument(
        "-b",
        "--port-bpod",
        type=str,
        default="/dev/ttyACM0",
        dest="serial_port_bpod",
        help="Serial port for Bpod",
    )
    p.add_argument(
        "device", type=str, help="Device key from the setup YAML (e.g. 'bpod')"
    )
    p.add_argument(
        "action",
        type=str,
        help="Action name (e.g. 'valve_pulse', 'valve_flush')",
    )
    p.add_argument(
        "params",
        nargs="*",
        metavar="KEY=VALUE",
        help="Optional action parameters (e.g. valve_id=1 duration_s=0.025)",
    )
    _add_dev_args(p)
    p.set_defaults(func=run_action)


def make_subparser_register(sub_parsers):
    """Legacy subject registration subcommand — use 'subject' instead."""
    examples = dedent(
        f"""Examples (legacy — prefer: msw subject add/rename/remove):

    msw register add -s _test_subject
    msw register add -s _test_subject -t probabilistic_switching
    msw register remove -s _test_subject
    msw register rename -s _test_subject -n _test_subject_renamed

Available tasks:
{available_tasks}

    """
    )
    p = sub_parsers.add_parser(
        "register",
        description="Legacy subject registration (prefer: msw subject add/rename/remove)",
        help="[legacy] Register subjects — use 'subject' instead",
        epilog=examples,
        formatter_class=ArgparseFormatter,
    )
    p.add_argument(
        "subcommand",
        choices=["add", "remove", "rename"],
        help="add / remove / rename",
    )
    p.add_argument(
        "-s", "--subject", type=str, default="_test_subject", dest="subject"
    )
    p.add_argument("-t", "--task", type=str, default="", dest="task")
    p.add_argument(
        "-o", "--out-path", type=str, default=default_out_path, dest="out_path"
    )
    p.add_argument(
        "-cd", "--config-dir", type=str, default="", dest="config_dir"
    )
    p.add_argument(
        "-n",
        "--new-alias",
        dest="new_alias",
        type=str,
        default="",
        help="New alias when subcommand is 'rename'",
    )
    p.add_argument(
        "-m",
        "--move-data",
        dest="move_data",
        default=True,
        action="store_true",
        help="Move existing session data to new subject name when renaming",
    )
    p.add_argument("--force", action="store_true", default=False)
    p.set_defaults(func=run_register)


def parse_args(args=None):
    epilog = dedent(
        """\
        Source: https://github.com/larsrollik/murineshiftwork

        """
    )
    main_parser = ArgumentParser(
        prog="msw",
        description=(
            "Murine Shift Work (msw) — behavioural task acquisition with hardware support.\n"
            f"Version {_MSW_VERSION} | © Lars B. Rollik | PolyForm Internal Use 1.0.0"
        ),
        epilog=epilog,
        formatter_class=ArgparseFormatter,
    )
    main_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"msw {_MSW_VERSION}",
        help="Show version and exit",
    )
    sub_parsers = main_parser.add_subparsers(metavar="command", dest="command")
    sub_parsers.required = True
    make_subparser_init(sub_parsers)
    make_subparser_setup(sub_parsers)
    make_subparser_subject(sub_parsers)
    make_subparser_run(sub_parsers)
    make_subparser_calibration(sub_parsers)
    make_subparser_action(sub_parsers)
    make_subparser_register(sub_parsers)

    parsed_args = main_parser.parse_args(args=args)
    return parsed_args.__dict__
