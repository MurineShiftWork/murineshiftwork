import logging
import random
from datetime import datetime

import numpy as np
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from tqdm import tqdm

from shift_work.tools.calibration_handling import load_water_calibration
from shift_work.tools.calibration_handling import save_water_calibration
from shift_work.tools.gui import ask_water_calibration_ready
from shift_work.tools.gui import ask_water_calibration_weight

calibration_data = load_water_calibration()

VALVE_TIME_MIN = 10  # ms
VALVE_TIME_MAX = 100  # ms
VALVE_TIME_STEP = 20  # ms

VALVE_TIMES_TO_TEST = np.linspace(
    VALVE_TIME_MIN,
    VALVE_TIME_MAX,
    int(VALVE_TIME_MAX / VALVE_TIME_STEP),
    endpoint=False,
)

VALVE_ITERATIONS = 200
VALVE_INTER_PULSE_INTERVAL = 0.1

VALVES_TO_CALIBRATE = [1, 3]


def run_test_water_drops(
    valve=1,
    valve_open_time=10,
    n_trials=VALVE_ITERATIONS,
    inter_pulse_interval=VALVE_INTER_PULSE_INTERVAL,
    bpod=None,
):
    if valve_open_time > 0.5:
        corrected_valve_time = round(valve_open_time / 1000, 3)
        logging.warn(
            f"Valve times not converted to ms yet.. Valve time of {valve_open_time}s is {corrected_valve_time}ms"
        )
        valve_open_time = corrected_valve_time

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
    n_drops=VALVE_ITERATIONS,
    inter_pulse_interval=VALVE_INTER_PULSE_INTERVAL,
    bpod=None,
):
    calibration_data = load_water_calibration()

    ask_water_calibration_ready(valve=valve)

    run_test_water_drops(
        valve=valve,
        valve_open_time=valve_open_time,
        n_trials=n_drops,
        inter_pulse_interval=inter_pulse_interval,
        bpod=bpod,
    )

    weight = ask_water_calibration_weight()
    weight_per_drop = round(weight / n_drops, 3)

    def add_calibration_data_measurement():
        return {
            "measurement_time": datetime.now(),
            "valve": valve,
            "valve_time": valve_open_time,
            "n_drops": n_drops,
            "inter_pulse_interval": inter_pulse_interval,
            "weight": weight,
            "weight_per_drop": weight_per_drop,
            "microliters": weight_per_drop * 1000,
        }

    if calibration_data.empty:
        import pandas as pd

        calibration_data = pd.DataFrame([add_calibration_data_measurement()])
    else:
        calibration_data = calibration_data.append(
            {
                "measurement_time": datetime.now(),
                "valve": valve,
                "valve_time": valve_open_time,
                "n_drops": n_drops,
                "inter_pulse_interval": inter_pulse_interval,
                "weight": weight,
                "weight_per_drop": weight_per_drop,
                "microliters": weight_per_drop * 1000,
            },
            ignore_index=True,
        )

    # fixme: removing manually weird columns
    calibration_data = calibration_data[
        calibration_data.columns.drop(list(calibration_data.filter(regex="Unnamed")))
    ]
    save_water_calibration(df=calibration_data)


random_valve_times = VALVE_TIMES_TO_TEST.copy()
random.shuffle(random_valve_times)


bpod = Bpod()
for valve in [1, 3]:
    for valve_time in random_valve_times:
        print(f"valve: {valve}, with valve time: {valve_time}")
        calibrate_point_for_valve(
            valve=valve,
            valve_open_time=valve_time,
            n_drops=VALVE_ITERATIONS,
            inter_pulse_interval=VALVE_INTER_PULSE_INTERVAL,
            bpod=bpod,
        )
bpod.close()

if __name__ == "__main__":
    print("main")
