import argparse


class ArgparseFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    pass


DEFAULT_REMOTE_IP = "localhost"
DEFAULT_REMOTE_PORT = 37497


def run_status(**kwargs):
    print("TODO: get status of OE remote here")


def add_subparser_status(sub_parser=None):
    parser_status = sub_parser.add_parser(name="status")

    gr = parser_status.add_argument_group()
    gr.add_argument()

    parser_status.set_defaults(func=run_status)


# TODO: add other subparser here for: settings, preview, stop, record


def parse_args(args=None):
    main_parser = argparse.ArgumentParser(
        "Open Ephys Remote Control",
        formatter_class=ArgparseFormatter,
    )
    sub_parsers = main_parser.add_subparsers(metavar="command", dest="command")
    sub_parsers.required = True

    add_subparser_status(sub_parser=sub_parsers)

    parsed_args = main_parser.parse_args(args=args)
    return parsed_args.__dict__

    # TODO: move these groups into subfunctions, then hook into subparsers
    # BASE
    main_group = parser.add_argument_group("Base")
    main_group.add_argument(
        "-ip",
        "--remote-ip",
        dest="remote_ip",
        type=str,
        default=DEFAULT_REMOTE_IP,
        help="Remote IP address",
    )
    main_group.add_argument(
        "-port",
        "--remote-port",
        dest="remote_port",
        type=int,
        default=DEFAULT_REMOTE_PORT,
        help="Remote port",
    )
    # ACTIONS
    action_group = parser.add_argument_group("Actions")
    action_group.add_argument(
        "--status",
        dest="status",
        action="store_true",
        default=False,
        help="Get status",
    )
    action_group.add_argument(
        "--settings",
        dest="settings",
        action="store_true",
        default=False,
        help="Get settings",
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
    # SETTINGS
    settings_group = parser.add_argument_group("Settings")
    settings_group.add_argument(
        "--append-text",
        dest="append_text",
        type=str,
        default="",
        help="Append text",
    )
    settings_group.add_argument(
        "--base-text",
        dest="base_text",
        type=str,
        default="",
        help="Base text",
    )
    settings_group.add_argument(
        "--prepend-text",
        dest="prepend_text",
        type=str,
        default="",
        help="Prepend text",
    )
    settings_group.add_argument(
        "-dir",
        "--parent-directory",
        dest="parent_directory",
        type=str,
        default="",
        help="Parent directory",
    )
    # Option
    settings_group = parser.add_argument_group("Options")
    action_group.add_argument(
        "--patch-all",
        dest="patch_all_record_nodes",
        action="store_true",
        default=False,
        help="Patch settings on all record nodes",
    )

    return parser
