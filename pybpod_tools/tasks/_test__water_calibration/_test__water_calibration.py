import logging

import numpy as np
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from tqdm import tqdm

from pybpod_tools.tools.calibration_handling import load_water_calibration

calibration_data = load_water_calibration()


def run_test_value(
    valve=1, valve_open_time=10, n_trials=200, inter_pulse_interval=0.05, bpod=None
):
    for _ in tqdm(np.arange(n_trials)):
        sma = StateMachine(bpod=bpod)
        sma.add_state(
            state_name="valve_open",
            state_timer=valve_open_time,
            state_change_conditions={"Tup": "iti"},
            output_actions=[(Bpod.OutputChannels.Valve, valve)],
        )

        sma.add_state(
            state_name="iti",
            state_timer=inter_pulse_interval,
            state_change_conditions={"Tup": "exit"},
            output_actions=[],
        )

        bpod.send_state_machine(sma)
        if not bpod.run_state_machine(sma):
            break


calibrating = True
while calibrating:
    # if data: fit + show

    pass

# figure: show calibration_data curve raw and normalised by drops
# out data: dataframe of raw measurements. save to standard location
# out data: fitted curve for measurements
# -> save data at project level, but specify also board that was used and
# opening time + n_drops
#
# for drop in n_drops:
#     give drop
#     iti
#
# REPEAT for enough measurements to fit exponential
# TODO: IMPLEMENT
# TODO: ask for valve time, repeats, and water weight on command line with "input" function, then use plotext to plot curve for inspection which values to use next for full calibration_data
# TODO: implement line fit + save data + protocol needs to load calibration_data file and get correct value estimate from calibration_data curve
# calibration_data data: load from config_files folder
# while calibrating
#   level 1 options:
#       show calibration_data curve for 0-10uL -> plotext plot into cmd line for 0-10uL x and 0-?ms y
#       add point -> ask for opening time, nr pulses -> run pulses, ask for weight -> result is uL amount datapoint, save
#       remove point -> ask for opening time, then remove closest match, save


if __name__ == "__main__":
    print("main")
