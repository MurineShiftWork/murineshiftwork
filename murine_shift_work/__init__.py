# -*- coding: utf-8 -*-
#
# Author: Lars B. Rollik <L.B.Rollik@protonmail.com>
import logging

level = "DEBUG"
logger = logging.getLogger()
logger.setLevel(getattr(logging, level))

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s"
    " - %(processName)s %(filename)s:%(lineno)s"
    " - %(message)s"
)
formatter.datefmt = "%Y-%m-%d %H:%M:%S %p"

stream_handler = logging.StreamHandler()
stream_handler.setLevel(getattr(logging, level))
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

__version__ = "0.0.2.dev0"
__author__ = "Lars B. Rollik"


def start_gui():
    from murine_shift_work.logic.run_install_tasks import run_check_install
    from pybpodgui_plugin.__main__ import start

    run_check_install()
    start()
