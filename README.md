# Behaviour protocols via pybpod

---

##### TODO


- basic task file structure
    - task settings
    - session params
    - trial params
    - online plots
    - main task
    - implementation of sounds ?

- Tasks
    - PS
        - habituation: center init, side light, reward either side
        - training 'lenient': center init, side light, one side rewarded, but no timeout on wrong side chosen first
        - training 'strict' == task deterministic: center inint, side light, one side rewarded and only first choice rewarded
        - main task: blocks of 10/50/90 with block switch criterion on nr correct rolling mean
        - sub tasks:
            - stop signal: auditory cue after center init and pulled out
            - punish: stop signal ingnored and side in -> air puff
            - opto stim: init, move2side, choice, ?
    - OC
        - habituation to spout: pavlovian (not operant), reward cues, no neutral
        - training 'reward' (OC-R): operant, reward + neutral cues
        - training 'punish' (OC-P): operant, punish + neutral cues
    - Water calibration -> copy from iblrig


##### Usage

TODO...
