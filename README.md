# Behaviour protocols via pybpod

---

## TODO

- PS task
    - [x] Basic task structure for PS
    - [ ] sound output plays with sounddevice package and TTL is received correctly by bpod BNC input channel
    - [ ] task settings
    - [ ] session params
    - [ ] trial params
    - [ ] online plots
    - [ ] main tasks: PS without stopping, PS and stopping
        - blocks of 10/50/90 with block switch deterministic 40-60 trials or with criterion on nr correct rolling mean
        - stop signal: auditory cue after center init and pulled out
        - punish: stop signal ingnored and side in -> air puff
        - opto stim: init, move2side, choice, ?
    - [ ] training paradigms
        - habituation: center init, side light, reward either side
        - training 'lenient': center init, side light, one side rewarded, but no timeout on wrong side chosen first
        - training 'strict' == task deterministic: center inint, side light, one side rewarded and only first choice rewarded
    - [ ] Additional parameters and task considerations
        - ..


- test and maintenance modules
    - [ ] Water calibration -> copy from iblrig
    - [ ] sound/noise preparation funcitons -> check iblrig


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
2) Go to repository and run:
```
pip install -e .
```
3) Add users, boards, experiments, etc. to the main project from the PyBpod GUI.

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
