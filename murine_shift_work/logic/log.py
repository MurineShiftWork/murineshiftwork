import json
import logging

from rich import get_console
from rich.logging import RichHandler


def setup_logging(level=None):
    if level is None:
        level = "DEBUG"
    logger = logging.getLogger()

    if not logger.handlers:
        logger.setLevel(getattr(logging, level))

        formatter = logging.Formatter("%(message)s")
        formatter.datefmt = "%Y-%m-%d %H:%M:%S.%f"

        # file_handler = logging.FileHandler(filename="/tmp/log.txt")  # fixme: listen to config filename for log file
        # file_handler.setLevel(getattr(logging, level))
        # file_handler.setFormatter(formatter)
        # logger.addHandler(file_handler)
        console = get_console()
        console.record = True

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
        logging.info(f"Set up logging for rcc with level {level}")


def patch_logging_levels(target_level="WARNING"):
    for m in ["pybpodapi", "pybpodgui_api", "pybpodgui_plugin", "matplotlib"]:
        logger = logging.getLogger(m)
        logger.setLevel(target_level)


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
