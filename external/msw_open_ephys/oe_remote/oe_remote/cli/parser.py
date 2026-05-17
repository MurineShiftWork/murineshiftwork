import argparse

from oe_remote.cli.commands import cmd_preview, cmd_record, cmd_status, cmd_stop


class _Fmt(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    pass


_DEFAULT_IP = "localhost"
_DEFAULT_PORT = 37497
_DEFAULT_LOCAL_PATH = "/mnt/fastdata/data"
_DEFAULT_REMOTE_PATH = r"E:\\OE_DATA\\LBR\\"

_RECORD_DESCRIPTION = """\
Configure recording paths and start an Open Ephys recording.

Three modes are selected automatically based on the arguments provided:

  Standalone  (no --acquisition-extension, no --child)
    Use when ephys is the only session and no children are expected.
    Records to: {remote-path}/{subject}/{subject__dt__session-ext}/Record Node/

      oe-remote record --subject mouse1 --session-extension pxi

  Parent      (--acquisition-extension is set, no --child)
    Use when starting a multi-modal acquisition that will contain multiple
    sessions. Creates a named acquisition folder and records the first
    session inside it. Caches the acquisition path for --child @last.
    Records to: {remote-path}/{subject}/{subject__dt__acq-ext}/{subject__dt__session-ext}/Record Node/

      oe-remote record --subject mouse1 \\
        --acquisition-extension ephys_multi_behavior \\
        --session-extension pxi

  Child       (--child <acq_path> or --child @last)
    Use when adding a session to an already-started parent acquisition.
    Pass the acquisition folder path explicitly or use @last to reuse the
    most recently cached path.
    Records to: {remote-path}/{acq_path}/{subject__dt__session-ext}/Record Node/

      oe-remote record --subject mouse1 \\
        --session-extension intan_ttl \\
        --child @last
"""


def _add_connection(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Connection")
    g.add_argument(
        "-ip",
        "--remote-ip",
        dest="ip",
        default=_DEFAULT_IP,
        help="Open Ephys GUI host IP",
    )
    g.add_argument(
        "-port",
        "--remote-port",
        dest="port",
        type=int,
        default=_DEFAULT_PORT,
        help="Open Ephys HTTP API port",
    )
    g.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )


def _add_metadata(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Metadata / paths")
    g.add_argument(
        "--local-path",
        dest="local_path",
        default=_DEFAULT_LOCAL_PATH,
        help="Local base data directory",
    )
    g.add_argument(
        "--remote-path",
        dest="remote_path",
        default=_DEFAULT_REMOTE_PATH,
        help="Remote base data directory (as seen by Open Ephys GUI)",
    )
    g.add_argument(
        "--subject",
        dest="subject",
        default="_test_oe_controller",
        help="Subject identifier",
    )
    g.add_argument(
        "--session-extension",
        dest="session_extension",
        required=True,
        help="Session label appended to subject__datetime (e.g. pxi, intan_ttl)",
    )
    g.add_argument(
        "--acquisition-extension",
        dest="acquisition_extension",
        default="",
        help="Acquisition label for the parent folder (enables parent mode). "
        "Example: ephys_multi_behavior",
    )
    g.add_argument(
        "--child",
        "--is-child-session-to",
        dest="is_child_session_to",
        default="",
        metavar="ACQ_PATH",
        help="Add this session under an existing acquisition folder. "
        "Pass subject/acquisition_name or '@last' to use the most recently "
        "cached path.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oe-remote",
        description="Remote control for Open Ephys GUI v1+",
        formatter_class=_Fmt,
    )
    sub = parser.add_subparsers(metavar="command", dest="command")
    sub.required = True

    # status
    p = sub.add_parser(
        "status",
        formatter_class=_Fmt,
        help="Print current GUI mode (IDLE / ACQUIRE / RECORD)",
    )
    _add_connection(p)
    p.set_defaults(func=cmd_status)

    # preview
    p = sub.add_parser(
        "preview",
        formatter_class=_Fmt,
        help="Start acquisition (ACQUIRE mode, no recording)",
    )
    _add_connection(p)
    p.set_defaults(func=cmd_preview)

    # record
    p = sub.add_parser(
        "record",
        formatter_class=_Fmt,
        description=_RECORD_DESCRIPTION,
        help="Configure paths and start recording",
    )
    _add_connection(p)
    _add_metadata(p)
    p.set_defaults(func=cmd_record)

    # stop
    p = sub.add_parser(
        "stop", formatter_class=_Fmt, help="Stop acquisition / recording (IDLE mode)"
    )
    _add_connection(p)
    p.set_defaults(func=cmd_stop)

    return parser


def parse_args(args=None) -> dict:
    return build_parser().parse_args(args).__dict__
