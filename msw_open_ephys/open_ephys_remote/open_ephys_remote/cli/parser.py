import argparse

from open_ephys_remote.cli.execute import run_preview
from open_ephys_remote.cli.execute import run_record
from open_ephys_remote.cli.execute import run_status
from open_ephys_remote.cli.execute import run_stop


class ArgparseFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    pass


DEFAULT_REMOTE_IP = "localhost"
DEFAULT_REMOTE_PORT = 37497
DEFAULT_LOCAL_DATA_PATH = "/mnt/fastdata/data"


def add_group_base(parser=None):
    group_base = parser.add_argument_group("General")
    group_base.add_argument(
        "-ip",
        "--remote-ip",
        dest="ip",
        type=str,
        default=DEFAULT_REMOTE_IP,
        help="Remote IP address",
    )
    group_base.add_argument(
        "-port",
        "--remote-port",
        dest="port",
        type=int,
        default=DEFAULT_REMOTE_PORT,
        help="Remote port",
    )
    group_base.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Sets log level to DEBUG and enables additional development features",
    )


# def add_group_settings(parser=None):
#     settings_group = parser.add_argument_group("Settings")
#     settings_group.add_argument(
#         "--append-text",
#         dest="append_text",
#         type=str,
#         default="",
#         help="Append text",
#     )
#     settings_group.add_argument(
#         "--base-text",
#         dest="base_text",
#         type=str,
#         default="",
#         help="Base text",
#     )
#     settings_group.add_argument(
#         "--prepend-text",
#         dest="prepend_text",
#         type=str,
#         default="",
#         help="Prepend text",
#     )
#     settings_group.add_argument(
#         "-dir",
#         "--parent-directory",
#         dest="parent_directory",
#         type=str,
#         default="",
#         help="Parent directory",
#     )


def add_group_metadata(parser=None):
    settings_group = parser.add_argument_group("Metadata")
    settings_group.add_argument(
        "--local-path",
        dest="local_path",
        type=str,
        default=DEFAULT_LOCAL_DATA_PATH,
        help="Local path",
    )
    settings_group.add_argument(
        "--remote-path",
        dest="remote_path",
        type=str,
        default=r"E:\\\\OE_DATA\\\\LBR\\\\",
        help="Remote path",
    )
    settings_group.add_argument(
        "--subject",
        dest="subject",
        type=str,
        default="_test_oe_controller",
        help="Subject",
    )
    settings_group.add_argument(
        "--child",
        "--is-child-session-to",
        dest="is_child_session_to",
        type=str,
        default="",
        help="Child session main name like '_test_subject__{dt}__{acquisition_extension}'",
    )
    settings_group.add_argument(
        "--acquisition-extension",
        dest="acquisition_extension",
        type=str,
        default="ephys_multi_behavior",
        help="Acquisition extension",
    )
    settings_group.add_argument(
        "--session-extension",
        dest="session_extension",
        type=str,
        default="",
        help="Session extension",
    )


def add_subparser_status(sub_parser=None):
    parser_status = sub_parser.add_parser(
        name="status",
        formatter_class=ArgparseFormatter,
    )
    add_group_base(parser=parser_status)
    parser_status.set_defaults(func=run_status)


def add_subparser_preview(sub_parser=None):
    parser_status = sub_parser.add_parser(
        name="preview",
        formatter_class=ArgparseFormatter,
    )
    add_group_base(parser=parser_status)
    parser_status.set_defaults(func=run_preview)


def add_subparser_record(sub_parser=None):
    parser_status = sub_parser.add_parser(
        name="record",
        formatter_class=ArgparseFormatter,
    )
    add_group_base(parser=parser_status)
    add_group_metadata(parser=parser_status)
    parser_status.set_defaults(func=run_record)


def add_subparser_stop(sub_parser=None):
    parser_status = sub_parser.add_parser(
        name="stop",
        formatter_class=ArgparseFormatter,
    )
    add_group_base(parser=parser_status)
    parser_status.set_defaults(func=run_stop)


def parse_args(args=None):
    main_parser = argparse.ArgumentParser(
        "Open Ephys Remote Control",
        formatter_class=ArgparseFormatter,
    )
    sub_parsers = main_parser.add_subparsers(metavar="command", dest="command")
    sub_parsers.required = True

    add_subparser_status(sub_parser=sub_parsers)
    add_subparser_preview(sub_parser=sub_parsers)
    add_subparser_record(sub_parser=sub_parsers)
    add_subparser_stop(sub_parser=sub_parsers)

    parsed_args = main_parser.parse_args(args=args)
    return parsed_args.__dict__


# # Option
# settings_group = parser.add_argument_group("Options")
# action_group.add_argument(
#     "--patch-all",
#     dest="patch_all_record_nodes",
#     action="store_true",
#     default=False,
#     help="Patch settings on all record nodes",
# )
