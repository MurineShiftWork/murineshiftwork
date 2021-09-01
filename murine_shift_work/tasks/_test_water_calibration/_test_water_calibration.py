import logging
import random
import time

import numpy as np
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from tqdm import tqdm

from murine_shift_work.logic.calibration import CalibrationDataWater
from murine_shift_work.logic.gui import ask_water_calibration_ready
from murine_shift_work.logic.gui import ask_water_calibration_weight
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


def run_test_water_drops(
    valve=1,
    valve_open_time=10,
    n_trials=200,
    inter_pulse_interval=0.1,
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


class Task(TaskRunner):
    def run(self) -> None:
        VALVE_TIME_MIN = 10  # ms
        VALVE_TIME_MAX = 100  # ms
        VALVE_TIME_STEP = 20  # ms

        VALVE_TIMES_TO_TEST = np.linspace(
            VALVE_TIME_MIN,
            VALVE_TIME_MAX,
            int(VALVE_TIME_MAX / VALVE_TIME_STEP),
            endpoint=False,
        )

        N_DROPS = 200
        INTER_PULSE_INTERVAL = 0.1
        VALVES_TO_CALIBRATE = [1, 3]

        random_valve_times = VALVE_TIMES_TO_TEST.copy()
        random.shuffle(random_valve_times)

        calibration = CalibrationDataWater(
            file_path=self.input_kwargs["calibration_file_water"]
        )

        for valve_id in VALVES_TO_CALIBRATE:
            for valve_opening_time in random_valve_times:
                logging.info(
                    f"valve: {valve_id}, with valve time: {valve_opening_time}ms."
                )

                ask_water_calibration_ready(valve=valve_id)

                run_test_water_drops(
                    valve=valve_id,
                    valve_open_time=valve_opening_time,
                    n_trials=N_DROPS,
                    inter_pulse_interval=INTER_PULSE_INTERVAL,
                    bpod=self.bpod,
                )

                water_weight_g = ask_water_calibration_weight()

                calibration.add_calibration_point(
                    valve_id=valve_id,
                    valve_opening_time=valve_opening_time,
                    n_drops=N_DROPS,
                    inter_pulse_interval=INTER_PULSE_INTERVAL,
                    water_weight_g=water_weight_g,
                )

        logging.debug(f"\n{str(calibration)}\n")
        calibration.save()
        calibration.save_calibration_plot()


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        logging.info("Exiting TaskProcess WITH")
    logging.info("THE END run_task")


if __name__ == "__main__":
    print("main")
