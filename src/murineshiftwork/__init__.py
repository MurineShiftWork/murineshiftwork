# -*- coding: utf-8 -*-
#
# Author: Lars B. Rollik <L.B.Rollik@protonmail.com>
# License: PolyForm Internal Use 1.0.0
# Source: https://www.github.com/larsrollik/murineshiftwork.git
#
# Namespace package migration note
# ---------------------------------
# This __init__.py makes `murineshiftwork` a regular package (not a namespace package).
# When splitting into msw-namespace / msw-agent / msw-tasks sub-packages, this file
# must be REMOVED so Python treats `murineshiftwork/` as an implicit namespace package
# (PEP 420, no __init__.py at namespace root).
#
# Version pattern for namespace sub-packages
# -------------------------------------------
# Each sub-package (msw-namespace, msw-agent, msw-tasks, …) should read its version
# from the installed package metadata rather than repeating the string in code.
# Template:
#
#   from importlib.metadata import version, PackageNotFoundError
#   try:
#       __version__ = version("msw-namespace")   # ← use the pip install name
#   except PackageNotFoundError:
#       __version__ = "unknown"
#   __author__ = "Lars B. Rollik"
#
# The version string lives ONLY in pyproject.toml / setup.cfg — never repeated in code.
# Bump it there; importlib.metadata picks it up at import time.

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("murineshiftwork")
except PackageNotFoundError:
    __version__ = "unknown"

__author__ = "Lars B. Rollik"
