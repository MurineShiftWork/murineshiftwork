# -*- coding: utf-8 -*-
#
# Author: Lars B. Rollik <L.B.Rollik@protonmail.com>
# License: BSD 3-Clause
# Source code: https://www.github.com/larsrollik/murineshiftwork.git

__version__ = "1.0.0"
__author__ = "Lars B. Rollik"

from murineshiftwork.cli import run_cli
from murineshiftwork.logic.log import patch_logging_levels
from murineshiftwork.hardware.bpod import patch_user_settings
from murineshiftwork.readers.session import read_session_data

patch_logging_levels()
patch_user_settings()
