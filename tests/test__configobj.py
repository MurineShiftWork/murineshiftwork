import os
from pathlib import Path
from pprint import pprint

from configobj import ConfigObj

c = ConfigObj(
    infile=os.path.expanduser(
        "~/code/murine_shift_work/murine_shift_work/tasks/probabilistic_switching/task.settings"
    ),
    unrepr=True,
)

print(" ")

"""
read default settings
update with group
update with subject

"""
