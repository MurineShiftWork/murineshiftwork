import logging
from pathlib import Path


def run_register(**args_dict):
    """"""
    option = args_dict["subcommand"]

    if "add" in option:
        pass  # if not subject in args_dict["settings.subjects.all"], then add plus add task section below, write to config file and exit
    elif "remove" in option:
        pass  # if subject in args_dict["settings.subjects.all"], then remove section, write config file and exit
    elif "move" in option:
        pass  # if subject in args_dict["settings.subjects.all"], then rename subject section, write config file
        # if "--move-data", then find data dir and move subject dir if exists
    else:
        raise ValueError(f"Unknown option '{option}'")

    print(" ")


def run_task(**args_dict):
    """
    msw run -s subject -t task
    msw run -s subject -t task -p serial_port

    """
    task_name = args_dict["task"]
    exec(
        f"from murine_shift_work.tasks.{task_name}.{task_name} import run_task",
        globals(),
    )
    run_task(**args_dict)
