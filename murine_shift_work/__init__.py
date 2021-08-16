# -*- coding: utf-8 -*-
#
# Author: Lars B. Rollik <L.B.Rollik@protonmail.com>
import logging

from murine_shift_work.logic.pybpod_helpers import patch_logging_levels
from murine_shift_work.logic.pybpod_helpers import patch_user_settings
from murine_shift_work.logic.task_process import run_msw_cli


# General logger
level = "DEBUG"
logger = logging.getLogger()
logger.setLevel(getattr(logging, level))

formatter = logging.Formatter(
    "%(asctime)s.%(msecs)03d - %(levelname)s"
    " - %(processName)s %(filename)s:%(lineno)s"
    " - %(message)s"
)
formatter.datefmt = "%Y-%m-%d %H:%M:%S"

stream_handler = logging.StreamHandler()
stream_handler.setLevel(getattr(logging, level))
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Prepare pybpod package
patch_user_settings()
patch_logging_levels()

# Metadata
__version__ = "0.0.2.dev0"
__author__ = "Lars B. Rollik"


# Entrypoints
def run_msw_gui():
    from murine_shift_work.logic.run_install_tasks import run_check_install
    from pybpodgui_plugin.__main__ import start

    run_check_install()
    start()
