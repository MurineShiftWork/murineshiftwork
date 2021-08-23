# -*- coding: utf-8 -*-
#
# Author: Lars B. Rollik <L.B.Rollik@protonmail.com>
__version__ = "0.1.0.dev0"
__author__ = "Lars B. Rollik"

from murine_shift_work.cli import run_cli
from murine_shift_work.logic.pybpod_helpers import patch_logging_levels
from murine_shift_work.logic.pybpod_helpers import patch_user_settings

patch_user_settings()
patch_logging_levels()


# Entrypoints
def run_gui():
    from murine_shift_work.logic.run_install_tasks import run_check_install
    from pybpodgui_plugin.__main__ import start

    run_check_install()
    start()
