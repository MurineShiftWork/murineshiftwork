import logging
import random
import time

import numpy as np
from serial_weighing_scale import SerialWeighingScale
from tqdm import tqdm

from murineshiftwork.logic.calibration import CalibrationDataWater
from murineshiftwork.logic.config_io import update_valve_calibration
from murineshiftwork.logic.specific_state_machines import make_sma_for_drop_of_water
from murineshiftwork.logic.task_process import TaskProcess
from murineshiftwork.logic.task_process import TaskRunner


class Task(TaskRunner):
    def run(self) -> None:
        s = self.input_kwargs.get("settings.task.patched", {})

        VALVE_TIME_MIN = int(s.get("VALVE_TIME_MIN", 10))
        VALVE_TIME_MAX = int(s.get("VALVE_TIME_MAX", 100))
        VALVE_TIME_STEP = int(s.get("VALVE_TIME_STEP", 20))
        N_DROPS = int(s.get("N_DROPS", 400))
        INTER_PULSE_INTERVAL = float(s.get("INTER_PULSE_INTERVAL", 0.15))
        VALVES_TO_CALIBRATE = list(s.get("VALVES_TO_CALIBRATE", [1, 3]))
        PRECISION_DECIMALS = 2

        # Setup config write-back: requires --setup <name> on the CLI
        config_dir = self.input_kwargs.get("config_dir", "")
        setup_name = self.input_kwargs.get("setup", "")
        force_save = bool(s.get("force_save_calibration", False))

        VALVE_TIMES_TO_TEST = np.linspace(
            VALVE_TIME_MIN,
            VALVE_TIME_MAX,
            int(VALVE_TIME_MAX / VALVE_TIME_STEP),
            endpoint=False,
        )

        random_valve_times = VALVE_TIMES_TO_TEST.copy()
        random.shuffle(random_valve_times)

        scale = SerialWeighingScale(
            serial_port=self.input_kwargs["serial_port_scale"]
        )
        scale.start()  # blocks until firmware responds to <i> — scale is ready here

        scale.tare()
        post_tare = scale.read_weight_blocking()
        print(f"Scale ready. Weight post-tare: {post_tare} g")

        calibration = CalibrationDataWater(
            file_path=self.input_kwargs["calibration_file_water"]
        )

        for valve_id in VALVES_TO_CALIBRATE:
            for valve_opening_time in random_valve_times:
                logging.info(
                    f"valve: {valve_id}, with valve time: {valve_opening_time}ms."
                )

                if valve_opening_time > 0.5:
                    corrected_valve_time = np.round(
                        valve_opening_time / 1000, 3
                    )
                    logging.warn(
                        f"Valve times not converted to ms yet.. "
                        f"Valve time of {valve_opening_time}s is {corrected_valve_time}ms"
                    )
                    valve_opening_time = corrected_valve_time

                weight_before = scale.read_weight_blocking()
                logging.info(
                    f"Valve {valve_id} with {valve_opening_time}ms. Weight BEFORE: {weight_before} g"
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

                time.sleep(1)  # let liquid settle on pan before reading
                weight_after = scale.read_weight_blocking()
                logging.info(
                    f"Valve {valve_id} with {valve_opening_time}ms. Weight AFTER: {weight_after} g"
                )

                water_weight_g = np.round(
                    weight_after - weight_before, PRECISION_DECIMALS
                )
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

        # Save raw CSV (backward compat, always)
        logging.debug(f"\n{str(calibration)}\n")
        calibration.save(overwrite=True)
        calibration.save_calibration_plot()

        # Write back to SetupConfig YAML — one valve at a time, only if valid
        if config_dir and setup_name and not setup_name.startswith("unknown_"):
            for valve_id in VALVES_TO_CALIBRATE:
                try:
                    new_cal = calibration.to_valve_calibration(valve_id)
                except ValueError as e:
                    logging.warning(f"Skipping setup config write for valve {valve_id}: {e}")
                    continue

                is_valid, reason = new_cal.validate()
                status = "PASS" if is_valid else "FAIL"
                print(
                    f"[Valve {valve_id}] Curve validation: {status} — {reason}"
                )

                written = update_valve_calibration(
                    config_dir=config_dir,
                    setup_name=setup_name,
                    valve_id=valve_id,
                    new_calibration=new_cal,
                    force=force_save,
                )
                if written:
                    print(
                        f"[Valve {valve_id}] Written to {setup_name}.yaml "
                        f"({len(new_cal.points)} points, updated {new_cal.updated})"
                    )
                else:
                    print(
                        f"[Valve {valve_id}] NOT written — curve invalid. "
                        f"Re-run with force_save_calibration=True to override."
                    )
        else:
            logging.info(
                "No --setup name provided; calibration written to CSV only. "
                "Pass --setup <name> to also update the setup config YAML."
            )


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
