import json
import logging
from datetime import datetime
from pathlib import Path

from rich import get_console
from rich.logging import RichHandler

from murineshiftwork.logic.paths import MSW_DATETIME_FORMAT

# IDs of handlers that MSW owns on the root logger — anything else is third-party.
_MSW_ROOT_HANDLER_IDS: set[int] = set()

_CENTRAL_LOG_DIR = Path("~/.murineshiftwork/logs").expanduser()
_MAX_LOG_FILES = 100


def get_default_log_file_path(path=None):
    """Kept for backward compatibility — returns central log dir path."""
    return str(_CENTRAL_LOG_DIR)


def setup_logging(level=None, log_file=None, task="", subject="", setup=""):
    if level is None:
        level = "DEBUG"

    logger = logging.getLogger()

    if logger.handlers:
        return

    logger.setLevel(getattr(logging, level))

    formatter = logging.Formatter("%(message)s")
    formatter.datefmt = "%Y-%m-%d %H:%M:%S.%f"

    # Central log: one timestamped file per run; prune to _MAX_LOG_FILES
    if log_file:
        central_log_path = Path(log_file).expanduser()
        central_log_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        _CENTRAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
        dt = datetime.now().strftime(MSW_DATETIME_FORMAT)
        _parts = [p for p in [setup, dt, subject, task] if p]
        stem = "--".join(_parts)
        central_log_path = _CENTRAL_LOG_DIR / f"{stem}.log"
        all_logs = sorted(_CENTRAL_LOG_DIR.glob("*.log"))
        for old in all_logs[:-_MAX_LOG_FILES]:
            try:
                old.unlink()
            except OSError:
                pass

    file_handler = logging.FileHandler(filename=str(central_log_path))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    _MSW_ROOT_HANDLER_IDS.add(id(file_handler))

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

    logging.info(f"Logging to {central_log_path}")


def add_session_log_handler(session_file_path: str, level: str = "INFO"):
    """Add a per-session FileHandler writing INFO+ records to the session folder."""
    log_path = Path(str(session_file_path) + ".msw.log")
    handler = logging.FileHandler(filename=str(log_path))
    handler.setLevel(getattr(logging, level.upper()))
    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
    formatter.datefmt = "%Y-%m-%d %H:%M:%S"
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    _MSW_ROOT_HANDLER_IDS.add(id(handler))
    logging.info(f"Session log: {log_path}")


def patch_logging_levels(target_level="WARNING"):
    for m in ["pybpodapi", "pybpodgui_api", "pybpodgui_plugin", "matplotlib"]:
        logger = logging.getLogger(m)
        logger.setLevel(target_level)


def suppress_third_party_console_handlers():
    """Remove foreign StreamHandlers from all loggers to eliminate duplicate console output."""

    def _is_foreign_stream_handler(h: logging.Handler) -> bool:
        return isinstance(h, logging.StreamHandler) and not isinstance(
            h, logging.FileHandler
        )

    root = logging.getLogger()
    for handler in list(root.handlers):
        if (
            _is_foreign_stream_handler(handler)
            and id(handler) not in _MSW_ROOT_HANDLER_IDS
        ):
            root.removeHandler(handler)
            logging.debug("Removed foreign StreamHandler from root logger")

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
