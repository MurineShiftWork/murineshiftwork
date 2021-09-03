# -*- coding: utf-8 -*-
#
# Author: Lars B. Rollik <L.B.Rollik@protonmail.com>
# License: BSD 3-Clause
# Source code: https://www.github.com/larsrollik/murine_shift_work.git

__version__ = "0.1.0.dev0"
__author__ = "Lars B. Rollik"

from murine_shift_work.cli import run_cli
from murine_shift_work.logic.log import patch_logging_levels
from murine_shift_work.logic.pybpod_helpers import patch_user_settings

patch_logging_levels()
patch_user_settings()
