import logging
import os
from pathlib import Path
from pprint import pprint

from configobj import ConfigObj


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
