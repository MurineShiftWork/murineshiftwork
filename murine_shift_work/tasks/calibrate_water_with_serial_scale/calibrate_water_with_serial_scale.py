import json
import logging
import random
import time

import numpy as np
from serial_weighing_scale import connect_serial_scale
from serial_weighing_scale import SerialWeighingScale
from tqdm import tqdm

from murine_shift_work.logic.calibration import CalibrationDataWater
from murine_shift_work.logic.specific_state_machines import make_sma_for_drop_of_water
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


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

        N_DROPS = 10
        INTER_PULSE_INTERVAL = 0.1
        VALVES_TO_CALIBRATE = [1, 3]

        random_valve_times = VALVE_TIMES_TO_TEST.copy()
        random.shuffle(random_valve_times)

        scale = SerialWeighingScale(
            port=self.input_kwargs["serial_port_scale"]
        )  # default is: "/dev/ttyACM2"
        scale.tare_scale()

        calibration = CalibrationDataWater(
            file_path=self.input_kwargs["calibration_file_water"]
        )

        for valve_id in VALVES_TO_CALIBRATE:
            for valve_opening_time in random_valve_times:
                logging.info(
                    f"valve: {valve_id}, with valve time: {valve_opening_time}ms."
                )

                if valve_opening_time > 0.5:
                    corrected_valve_time = np.round(valve_opening_time / 1000, 3)
                    logging.warn(
                        f"Valve times not converted to ms yet.. "
                        f"Valve time of {valve_opening_time}s is {corrected_valve_time}ms"
                    )
                    valve_opening_time = corrected_valve_time

                weight_before = scale.read_weight_reliable()
                logging.info(
                    f"Valve {valve_id} with {valve_opening_time}ms. Weight BEFORE: {weight_before}"
                )

                for _ in tqdm(np.arange(N_DROPS)):
                    sma = make_sma_for_drop_of_water(
                        bpod=self.bpod,
                        valve_opening_time=valve_opening_time,
                        valve_ids=valve_id,
                        inter_drop_interval=INTER_PULSE_INTERVAL,
                    )

                    self.bpod.send_state_machine(sma)
                    if not self.bpod.run_state_machine(sma):
                        break

                # _ = scale.read_weight_reliable()
                time.sleep(1)
                weight_after = scale.read_weight_reliable()
                logging.info(
                    f"Valve {valve_id} with {valve_opening_time}ms. Weight AFTER: {weight_after}"
                )

                water_weight_g = weight_after - weight_before
                logging.info(
                    f"Valve {valve_id} with {valve_opening_time}ms. Weight DIFF: {water_weight_g}"
                )

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
