import logging
from pkgutil import iter_modules

import numpy as np
import serial


def unpack_input_dict(overwrite_dict, default_dict):
    for k, v in overwrite_dict.items():
        default_dict[k] = v
    return default_dict


def list_submodules(module):
    submodules = []
    for submodule in iter_modules(module.__path__):
        submodules.append(submodule.name)
    return submodules


def test_serial_port_is_accessible(port=None, baudrate=115200, timeout=1):
    try:
        device = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        device.isOpen()
    except IOError:
        return False
    return True


def list_available_tasks(detailed=False):
    from pathlib import Path
    import murineshiftwork.tasks as _tasks_pkg

    tasks_dir = Path(_tasks_pkg.__path__[0]) if hasattr(_tasks_pkg, "__path__") else None
    if tasks_dir is None or not tasks_dir.exists():
        # Namespace-package fallback: locate via installed package file
        import murineshiftwork
        tasks_dir = Path(murineshiftwork.__file__).parent / "tasks"

    summary = {}
    for item in sorted(tasks_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("_") or (
            item.is_dir() and item.name.startswith("_test_")
        ):
            if (item / f"{item.name}.py").exists():
                summary[item.name] = item

    if detailed:
        return summary
    else:
        return list(summary.keys())


def find_task_by_name(task_name=None, ignore_error=True):
    available_tasks = list_available_tasks()
    found = [x for x in available_tasks if task_name in x]
    if len(found) == 1:
        return found[0]
    elif len(found) == 0:
        return None
    else:
        msg = f"Task name '{task_name}' is not specific to any available task: {available_tasks}\n Selecting first one: {sorted(found)[0]}"
        logging.debug(msg)
        if ignore_error:
            return sorted(found)[0]
        else:
            raise ValueError(msg)


def print_box(msg=None, indent=2):
    """Print text box.
    Similar to: https://stackoverflow.com/questions/39969064/how-to-print-a-message-box-in-python
    """
    lines = msg.split("\n")
    width = max(map(len, lines))
    space = " " * indent

    top = f"+{'-' * (width + 2*indent)}+\n"
    line_strings = [f"|{space}{line:<{width}}{space}|\n" for line in lines]
    text_body = "".join(line_strings)

    print(top + text_body + top)


def draw_jittered_trial_time(start, stop, step=None, poisson=False):
    time_range = np.abs(stop - start)
    available_time_steps = np.linspace(
        start=start,
        stop=stop,
        num=int(np.round(time_range / step)) + 1,
        endpoint=True,
    )

    if poisson:
        raise NotImplementedError(
            "TODO: draw ITI as Poisson-distributed instead of linear"
        )
    else:
        drawn_trial_time = available_time_steps[
            np.random.randint(0, len(available_time_steps))
        ]

    return drawn_trial_time
