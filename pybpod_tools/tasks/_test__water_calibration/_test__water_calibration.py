import logging
import random

import numpy as np
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from tqdm import tqdm

from pybpod_tools.tools.calibration_handling import load_water_calibration

calibration_data = load_water_calibration()

VALVE_TIME_MIN = 10  # ms
VALVE_TIME_MAX = 200  # ms
VALVE_TIME_STEP = 20  # ms

VALVE_TIMES_TO_TEST = np.linspace(
    VALVE_TIME_MIN,
    VALVE_TIME_MAX,
    int(VALVE_TIME_MAX / VALVE_TIME_STEP),
    endpoint=False,
)

VALVE_ITERATIONS = 200
VALVE_INTER_PULSE_INTERVAL = 0.05

VALVES_TO_CALIBRATE = [1, 3]


def run_test_water_drops(
    valve=1,
    valve_open_time=10,
    n_trials=VALVE_ITERATIONS,
    inter_pulse_interval=VALVE_INTER_PULSE_INTERVAL,
    bpod=None,
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


def calibrate_point_for_valve(
    valve=1,
    valve_open_time=10,
    n_trials=VALVE_ITERATIONS,
    inter_pulse_interval=VALVE_INTER_PULSE_INTERVAL,
    bpod=None,
):
    calibration_data = load_water_calibration()

    run_test_water_drops(
        valve=valve,
        valve_open_time=valve_open_time,
        n_trials=n_trials,
        inter_pulse_interval=inter_pulse_interval,
        bpod=bpod,
    )

    print(
        calibration_data
    )  # fixme: check for weight of calibration drops -> add to calibration data


random_valve_times = VALVE_TIMES_TO_TEST.copy()
random.shuffle(random_valve_times)

for valve_time in random_valve_times:
    print(valve_time)


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
