import os
from pathlib import Path
from pprint import pprint

from configobj import ConfigObj


def read_config(file=None, unrepr=True):
    if not Path(file).exists():
        raise FileNotFoundError(str(file))

    return ConfigObj(infile=str(file), unrepr=unrepr)
