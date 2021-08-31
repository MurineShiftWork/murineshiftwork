import logging
from pathlib import Path
from shutil import copyfile

from configobj import ConfigObj
from rich.logging import RichHandler


def read_config(file=None, unrepr=True):
    if not Path(file).exists():
        raise FileNotFoundError(str(file))

    return ConfigObj(infile=str(file), unrepr=unrepr, list_values=True).dict()


def setup_logging(level=None):
    if level is None:
        level = "DEBUG"
    logger = logging.getLogger()

    if not logger.handlers:
        logger.setLevel(getattr(logging, level))

        formatter = logging.Formatter("%(message)s")
        formatter.datefmt = "%Y-%m-%d %H:%M:%S.%f"

        logging_handler = RichHandler(
            level=level,
            enable_link_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        logging_handler.setFormatter(formatter)
        logger.addHandler(logging_handler)
        logging.info(f"Set up logging for rcc with level {level}")


def update_config_file(in_dict=None, out_file=None, backup_extension="bak"):
    new_config = ConfigObj(in_dict, unrepr=True, list_values=True)
    dst = ".".join([str(out_file), backup_extension])
    copyfile(src=out_file, dst=dst)
    if not Path(dst).exists():
        raise FileNotFoundError(f"Config backup not found at {dst}")

    new_config.filename = out_file
    new_config.write()

    if not Path(new_config.filename).exists():
        raise FileNotFoundError(f"Config file not found at {out_file}")
