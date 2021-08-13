# Murine Shift Work: Behaviour protocols via pybpod

---

## Common problems

#### Pycharm debugger throws error `ControlList has no horizontal_headers attribute`, when starting GUI
Install pycharm version `2020.1.5`. Problems started after that and continue into the 2021 versions.

Temporary fix: add the following user env variables to the pycharm debugging configuration as suggested here
https://stackoverflow.com/questions/62040805/pycharm-debugger-getting-error-when-break-point-is-kept
```
PYDEVD_USE_CYTHON=NO
PYDEVD_USE_FRAME_EVAL=NO
```

## TODO

- Refactoring for commandline access
    - [x] finish main task_process class
    - [x] dry minimal_task example
    - **[No!]** update installation for task call via GUI  -->> USE SEPARATE VERSIONS UNTIL GUI NOT REQUIRED BY USERS. waste of time to debug GUI+net_port issue
    - [x] fix PS for CLI
    - [x] FIXME: instead of parsing from command line, find task settings.config in task dicts -->> this is a task specific requirement ? -> implemented as standard argparse
    - [ ] extend commandline/GUI split architecture to all task protocols


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

## Features
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

## Installation
1) Make an Anaconda environment
```
conda create -n py36 python=3.6 numpy pandas matplotlib scipy
conda activate py36
```

2) Setup up additional packages and sound
    a) Packages for bpod and pybpod gui to work
   ```bash
    # https://sites.google.com/site/bpoddocumentation/installing-bpod/ubuntu14
    sudo apt-get install linux-lowlatency

    #https://stackoverflow.com/questions/49333582/portaudio-library-not-found-by-sounddevice
    sudo apt-get install libportaudio2

    #https://stackoverflow.com/questions/60042568/this-application-failed-to-start-because-no-qt-platform-plugin-could-be-initiali
    sudo apt-get install qt5-default
   ```

    b) Sound settings
   Open `alsamixer` in the terminal and select sound device with `F6`, then set all outputs, particularly the gain to maximum values


3) Install this package with:
```
pip install -e .
```


3) Add users, boards, experiments, etc. to the main project and update git repo: both done via install task.
```NOTE: this is done via install_tasks script now.```

## Usage
Run the script `start_this_pybpod.py` to open the GUI and trigger the automatic update script
to add presets to the pybpod project.

## Support websites
[Bpod wiki](https://sites.google.com/site/bpoddocumentation)
[PyBpod docs](pybpod.readthedocs.io)
[PyBpod API docs](https://pybpod.readthedocs.io/projects/pybpod-api)
[PyBpod GUI docs](https://pybpod.readthedocs.io/projects/pybpod-gui-api)
[sounddevice](https://python-sounddevice.readthedocs.io)
[proplot](https://proplot.readthedocs.io)
