import json
import logging
from datetime import datetime
from pathlib import Path

from murineshiftwork.logic.paths import MSW_DATETIME_FORMAT

from rich import get_console
from rich.logging import RichHandler

# IDs of handlers that MSW owns on the root logger — anything else is third-party.
_MSW_ROOT_HANDLER_IDS: set[int] = set()


def get_default_log_file_path(path=None):
    if path is None:
        path = "/tmp/"

    path = Path(path)

    dt = datetime.now().strftime(MSW_DATETIME_FORMAT)
    out_name = f"murineshiftwork.{dt}.log"
    if path.is_dir():
        path = path / out_name
    else:
        path = path.parent / out_name
        logging.info(
            f"Given log file name, but ignoring in favour of: {str(path)}"
        )

    return str(path)


def setup_logging(level=None, log_file=None):
    if level is None:
        level = "DEBUG"

    if log_file is None:
        log_file = get_default_log_file_path()

    logger = logging.getLogger()

    if not logger.handlers:
        logger.setLevel(getattr(logging, level))

        formatter = logging.Formatter("%(message)s")
        formatter.datefmt = "%Y-%m-%d %H:%M:%S.%f"

        # To file
        file_handler = logging.FileHandler(filename=log_file)
        file_handler.setLevel(getattr(logging, level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        _MSW_ROOT_HANDLER_IDS.add(id(file_handler))

        # To console
        logging_handler = RichHandler(
            console=get_console(),
            level=level,
            enable_link_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        logging_handler.setFormatter(formatter)
        logger.addHandler(logging_handler)
        _MSW_ROOT_HANDLER_IDS.add(id(logging_handler))

        logging.info(
            f"Set up logging for MSW with level {level} and writing to '{log_file}'"
        )


def patch_logging_levels(target_level="WARNING"):
    for m in ["pybpodapi", "pybpodgui_api", "pybpodgui_plugin", "matplotlib"]:
        logger = logging.getLogger(m)
        logger.setLevel(target_level)


def suppress_third_party_console_handlers():
    """Remove foreign StreamHandlers from all loggers to eliminate duplicate console output.

    Third-party packages (rpi_camera_ensemble, one_axis_stage, …) may add their own
    StreamHandlers — either to named child loggers or directly to the root logger —
    before or after MSW's RichHandler is set up.  Both produce a line on the console
    for each record, giving the characteristic double-output.

    This function:
    - Removes any StreamHandler on the root logger that MSW did not register.
    - Removes all StreamHandlers from child loggers (they should propagate to root).
    File handlers are always preserved.  Safe to call multiple times.
    """
    def _is_foreign_stream_handler(h: logging.Handler) -> bool:
        return (
            isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        )

    # Root logger: only remove handlers that MSW did not add
    root = logging.getLogger()
    for handler in list(root.handlers):
        if _is_foreign_stream_handler(handler) and id(handler) not in _MSW_ROOT_HANDLER_IDS:
            root.removeHandler(handler)
            logging.debug("Removed foreign StreamHandler from root logger")

    # Child loggers: remove any console handler (they should let records propagate)
    for name, logger in logging.Logger.manager.loggerDict.items():
        if not isinstance(logger, logging.Logger):
            continue
        for handler in list(logger.handlers):
            if _is_foreign_stream_handler(handler):
                logger.removeHandler(handler)
                logging.debug(f"Removed StreamHandler from logger '{name}'")


def json_dumps_type_safe(data):
    return json.dumps(
        data,
        skipkeys=True,
        sort_keys=True,
        indent=4,
        default=lambda x: f"<NoJSON:{type(x)}>",
    )


def write_json(data=None, save_path=None):
    try:
        with open(save_path, "w") as f:
            txt = json_dumps_type_safe(data)
            f.write(txt)
            return True
    except BaseException:
        return False
