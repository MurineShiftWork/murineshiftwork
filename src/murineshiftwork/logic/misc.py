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
        # dsrdtr=False, rtscts=False: do not toggle DTR/RTS on open.
        # Toggling DTR resets Arduino-based devices (e.g. Bpod), which causes
        # the subsequent real connection attempt to read a mid-boot response.
        device = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            dsrdtr=False,
            rtscts=False,
        )
        device.close()
    except OSError:
        return False
    return True


def print_box(msg=None, indent=2):
    """Print text box.
    Similar to: https://stackoverflow.com/questions/39969064/how-to-print-a-message-box-in-python
    """
    lines = msg.split("\n")
    width = max(map(len, lines))
    space = " " * indent

    top = f"+{'-' * (width + 2 * indent)}+\n"
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
