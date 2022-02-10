<!--
-*- coding: utf-8 -*-

 Author: Lars B. Rollik <L.B.Rollik@protonmail.com>
 License:
-->
<!-- Banners -->

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)


# Murine Shift Work
Acquisition software for murine research
---

#### - Behaviour protocols via `pybpod-api`
#### - Video acquisition via `RPi Camera Colony`
#### - Remote control of ephys systems via `Open Ephys NetworkEvents`

---


### Features

- Command line interface (ready for high-level integration with GUI)

    ```bash
    # Add new subjects and register them for specific tasks
    murineshiftwork register ...

    # Run tasks and test/calibration protocols from one entrypoint
    murineshiftwork run --task [TASK] --subject [SUBJECT]
    ```

- Simple configuration via text files for subject/task settings

    ```bash
    # subject.settings
    [_test_subject]
        project = "test_project"
        experiment = "test_experiment"

        [[_test_minimal_task]]
            test_argument = "minimal"

        [[_test_video]]
            test_argument = "vid"

        [[probabilistic_switching]]
            probabilities = [(100,99), (99,100)]
            delay_until_center_init = [0.050, 0.060, 0.005]
            reward_amount_ul = 8
            criterion_contrast_blocks = .1

    ```

- Behavioural protocols
    - training 3 port center to out journey: This is a training stage for any 3-port arena task
    - probabilistic switching (PS): basic PS task
    - PS with stop signals: PS task with additional stop signals
        - all PS tasks implement additionally stimulation options for specific timepoints


- Test protocols
    - flush water, e.g. before session
    - sound and TTL test, e.g. does the sound play? and is the soundcard TTL received?
    - TTL outputs test, e.g. are the TTL for trial start and stimulation triggered and received by the connected systems?
    - water calibration, e.g. water by valve opening duration


- Synchronisation for parallel recordings (ephys, other, ..)
    - all tasks output a unique TTL sequence to identify the protocol in parallel ephys recordings


### Installation

#### Dependencies
- system: linux, tested with Ubuntu 18.04 and higher
- apt: `sudo apt-get install linux-lowlatency libportaudio2 qt5-default --upgrade -y`
- python: see `setup.py`

#### For deployment
1. `pip install git+https://llrrr@bitbucket.org/lbrcoding/murine_shift_work.git`

#### For development
1. `git clone https://llrrr@bitbucket.org/lbrcoding/murine_shift_work.git`
2. `pip install -e murine_shift_work[dev]`

### Usage

##### Registering subjects (& subjects to tasks)

##### Running tasks (& tests or calibration routines)
```bash
murineshiftwork run ...

```

See `murineshiftwork run -h` for all options and list of available tasks at end of help section:
```text
Available tasks:
    - _test_flush_water
    - _test_minimal_task
    - _test_open_ephys_remote
    - _test_pyqtgraph_app
    - _test_sound_and_ttl_in
    - _test_ttl_outputs
    - _test_video
    - _test_water_calibration
    - optotagging
    - periodic_trigger
    - probabilistic_switching
```

##### Starting remote ephys session
Generates folder structure for parent ephys session locally and on remote.

###### Path structure
- MSW: /base/subject/[subject__dt__task]
  - Ephys: /base/subject/[subject__dt__EPHYS]/ session data is in here
  - MSW child sessions:
    - /base/subject/[subject__dt__EPHYS]/[msw session folders]/[msw files + rcc files if video recorded]





1. CLI

```bash
remote-ephys-controller  --help

```

Alternative 1. Python module import

```python
import os
import time

from murine_shift_work.remote_ephys.controller import RemoteOpenEphysController

e = RemoteOpenEphysController(
    remote_ip="172.24.242.219",
    # remote_ip="192.168.100.48",
    remote_port=5558,
    remote_acquisition_path=r"E:\\OE_DATA\\LBR\\",
    acquisition_name="_test_subject",
    local_data_path=os.path.expanduser("~/data"),
)

# Control options:
e.start_preview()

e.start_recording()

time.sleep(2)

e.stop_recording()  # stops recording
e.stop_preview()  # stops recording & preview
```

2. Then initiate behaviour session with:

```bash
murineshiftwork run --is-child-session --out-path [/path/to/local/parent/session] ... [OTHER PARAMS] ... -s SUBJECT -t TASK
```



##### Load data

```python
from murine_shift_work.readers import read_session_data

session_dir = "/path/to/session_dir"
load_raw = False  # This is also the default value. Does not usually load the pybpod CSV.

session_data = read_session_data(session_dir=session_dir, load_raw=load_raw)

```


## TODO

- Refactoring for commandline access
    - [ ] add CLI option for adding directory where task lives, so that can extend MSW easily with other code
    - [x] Make refactoring notes
        - remove references to pybpod GUI. setup.py already adjusted.
    - [x] Log file for MSW and sub-modules [rcc] -> write to log file
    - [ ] remote ephys CLI
- [x] Reader module to load session data. current and legacy
- [ ]


## Fixes & install hints

- Ubuntu for 2+ monitors: (1) install Nvidia drivers from `software update -> additional drivers` menu, then (2) `sudo apt install lightdm`, (3) reboot, (4) `udo dpkg-reconfigure lightdm`
- Ubuntu VNC server install
 - `sudo apt install tigervnc-standalone-server` - [ref](https://www.answertopia.com/ubuntu/ubuntu-remote-desktop-access-with-vnc/)
 - `vncpasswd`
 - `~/.vnc/xstartup` and `chmod +x ~/.vnc/xstartup` - [ref](https://gitlab.gnome.org/GNOME/gnome-shell/-/issues/2196)
```bash
#!/bin/sh
[ -x /etc/vnc/xstartup ] && exec /etc/vnc/xstartup
[ -r $HOME/.Xresources ] && xrdb $HOME/.Xresources
vncconfig -iconic &
export DESKTOP_SESSION=/usr/share/xsessions/ubuntu.desktop
env GNOME_SHELL_SESSION_MODE=ubuntu dbus-launch --exit-with-session /usr/bin/gnome-session --systemd --session=ubuntu &
```
 - `vncserver -localhost no`
 - `sudo loginctl unlock-sessions` [ref](https://askubuntu.com/questions/1224957/i-cannot-log-in-a-vnc-session-after-the-screen-locks-authentification-error)

## Support websites
[Bpod wiki](https://sites.google.com/site/bpoddocumentation)

[PyBpod API docs](https://pybpod.readthedocs.io/projects/pybpod-api)

[sounddevice](https://python-sounddevice.readthedocs.io)

[RPi camera colony DEV](https://llrrr@bitbucket.org/lbrcoding/rpi_camera_colony_dev.git)

[RPi camera colony]( https://github.com/larsrollik/rpi_camera_colony.git)
