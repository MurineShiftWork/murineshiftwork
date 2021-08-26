import logging
import os
from pathlib import Path
from pprint import pprint
from shutil import copyfile

from configobj import ConfigObj


def read_config(file=None, unrepr=True):
    if not Path(file).exists():
        raise FileNotFoundError(str(file))

    return ConfigObj(infile=str(file), unrepr=unrepr, list_values=True).dict()


def setup_logging(level=None):
    if level is None:
        level = "INFO"
    logger = logging.getLogger()

    if not logger.handlers:
        logger.setLevel(getattr(logging, level))

        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d - %(levelname)s"
            " - %(filename)s:%(lineno)s"
            " - %(message)s"
        )
        formatter.datefmt = "%Y-%m-%d %H:%M:%S"

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(getattr(logging, level))
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)


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
