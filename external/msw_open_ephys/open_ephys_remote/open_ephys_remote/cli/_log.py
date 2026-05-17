import logging
from datetime import datetime
from pathlib import Path

from rich import get_console
from rich.logging import RichHandler


def get_default_log_file_path(path=None):
    if path is None:
        path = "/tmp/"

    path = Path(path)

    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"open_ephys_remote.{dt}.log"
    if path.is_dir():
        path = path / out_name
    else:
        path = path.parent / out_name
        logging.info(f"Given log file name, but ignoring in favour of: {str(path)}")

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

        logging.info(
            f"Set up logging for OpenEphysRemote with level {level} and writing to '{log_file}'"
        )
