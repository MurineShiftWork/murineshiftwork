import logging
from pkgutil import iter_modules

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


def test_port_accessible(port=None, baudrate=115200, timeout=1):
    try:
        device = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        device.isOpen()
    except IOError:
        return False
    return True


def list_available_tasks(detailed=False):
    import pkgutil
    from murine_shift_work import tasks as msw_tasks

    summary = {}
    for module in pkgutil.iter_modules(msw_tasks.__path__):
        summary[module.name] = module

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
        msg = f"Task name '{task_name}' is not specific to any available task: {available_tasks}"
        logging.debug(msg)
        if ignore_error:
            return None
        else:
            raise ValueError(msg)
