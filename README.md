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

```python
import os
import time

from remote_ephys.control_functions import RemoteEphysControl


e = RemoteEphysControl(
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


## TODO

- Refactoring for commandline access
    - [ ] add CLI option for adding directory where task lives, so that can extend MSW easily with other code
    - [ ] Make refactoring notes
        - remove references to pybpod GUI. setup.py already adjusted.
    - [ ] Log file for MSW and sub-modules [rcc] -> write to log file

    - [x] optotagging settings into json format
    - [x] CLI execute: register subcommands
    - [ ] install task adjustment for GUI run
    - [ ] patch updated settings nested
            - https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
            - https://stackoverflow.com/questions/5946236/how-to-merge-multiple-dicts-with-same-key-or-different-key
    - [ ] safe json serialisation with json.dumps(default=) - https://stackoverflow.com/questions/51674222/how-to-make-json-dumps-in-python-ignore-a-non-serializable-field
    - [ ] argparse key-value pairs - https://stackoverflow.com/questions/27146262/create-variable-key-value-pairs-with-argparse-python

    - [x] finish main task_process class
    - [x] dry minimal_task example
    - **[No!]** update installation for task call via GUI  -->> USE SEPARATE VERSIONS UNTIL GUI NOT REQUIRED BY USERS. waste of time to debug GUI+net_port issue
    - [x] fix PS for CLI
    - [x] FIXME: instead of parsing from command line, find task settings.config in task dicts -->> this is a task specific requirement ? -> implemented as standard argparse
    - [x] extend commandline/GUI split architecture to all task protocols


- Architecture
    - [x] Make online plotting with pyqtgraph QApplication wrapper. Create/close bpod outside, then hand Application as input arg.


- Tasks & settings
    - [x] Basic task structure for PS
    - [x] sound output plays with sounddevice package and TTL is received correctly by bpod BNC input channel
    - [x] task settings
    - [x] session params
    - [ ] trial params FROM SETTINGS TO PARADIGM are used from common variable set. At the moment, not all variables are set in settings, but some in task objects!
    - [x] general online plot for PS
    - Main tasks: PS without stopping, PS and stopping
        - [x] blocks of 10/50/90 with block switch ~~deterministic 40-60 trials or~~ with criterion on nr correct rolling mean
        - stop signal: auditory cue after center init and pulled out
        - punish: stop signal ingnored and side in -> air puff
        - opto stim: init, move2side, choice, ?
    - Other paradigms
        - [ ] Open field: ttl sequence + regular synch timestamps. maybe useful in future
        - [ ] Optotagging: excitatory, inhibitory -> several presets for standard opsins
    - ~~training paradigms~~
        - ~~habituation: center init, side light, reward either side~~
        - ~~training 'lenient': center init, side light, one side rewarded, but no timeout on wrong side chosen first~~
        - ~~training 'strict' == task deterministic: center inint, side light, one side rewarded and only first choice rewarded~~


- hardware
    - [x] build new arena with 3 ports on 3 different walls
    - [x] use valve 2 and 4 for air puffs -> set up air valves that get triggered via BNC from port PCB board contacts
    - [ ] set up all hardware on new ephys rig
        - bpod, pulsepal, 2x air valves, camera hardware (RPi shelf + usb power supply bank), pc+monitor+peripherals, ! network for RPi
        - power: bpod 12v, camera bank, pc, monitor, network switch, LED strip for daylight

- test and maintenance modules
    - [x] Water calibration -> quick procedure along lines of matlab bpod repo and iblrig
    - [x] sound/noise preparation functions -> similar to iblrig. only taken main sound generator
    - [ ] parameter GUI with pyqtgraph parameter tree from dict/list style object -> make converter from configobj to parametertree and back



## Support websites
[Bpod wiki](https://sites.google.com/site/bpoddocumentation)

[PyBpod API docs](https://pybpod.readthedocs.io/projects/pybpod-api)

[sounddevice](https://python-sounddevice.readthedocs.io)

[RPi camera colony DEV](https://llrrr@bitbucket.org/lbrcoding/rpi_camera_colony_dev.git)

[RPi camera colony]( https://github.com/larsrollik/rpi_camera_colony.git)
