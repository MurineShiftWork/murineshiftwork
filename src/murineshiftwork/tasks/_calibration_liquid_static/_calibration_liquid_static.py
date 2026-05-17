import logging
import random
import time

import numpy as np
from tqdm import tqdm

from murineshiftwork.hardware.bpod.water import make_sma_for_drop_of_water
from murineshiftwork.logic.calibration import (
    CalibrationDataWater,
    flag_outlier_points,
)
from murineshiftwork.logic.config import update_valve_calibration
from murineshiftwork.logic.scale import make_scale
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class Task(TaskRunner):
    def run(self) -> None:
        s = self.input_kwargs.get("settings.task.patched", {})

        VALVE_TIME_MIN = float(s.get("VALVE_TIME_MIN", 0.010))
        VALVE_TIME_MAX = float(s.get("VALVE_TIME_MAX", 0.100))
        VALVE_TIME_STEP = float(s.get("VALVE_TIME_STEP", 0.020))
        N_DROPS = int(s.get("N_DROPS", 400))
        INTER_PULSE_INTERVAL = float(s.get("INTER_PULSE_INTERVAL", 0.15))
        VALVES_TO_CALIBRATE = list(s.get("VALVES_TO_CALIBRATE", [1, 3]))
        SETTLE_TIME_S = float(s.get("SETTLE_TIME_S", 1.0))
        OUTLIER_SIGMA = float(s.get("OUTLIER_SIGMA_THRESHOLD", 2.5))
        PRECISION_DECIMALS = 4

        config_dir = self.input_kwargs.get("config_dir", "")
        setup_name = self.input_kwargs.get("setup", "")
        force_save = bool(s.get("force_save_calibration", False))

        VALVE_TIMES_TO_TEST = np.round(
            np.arange(
                VALVE_TIME_MIN,
                VALVE_TIME_MAX + VALVE_TIME_STEP / 2,
                VALVE_TIME_STEP,
            ),
            4,
        ).tolist()

        # --- Calibration plan overview ---
        n_conditions = len(VALVES_TO_CALIBRATE) * len(VALVE_TIMES_TO_TEST)
        total_drops = n_conditions * N_DROPS
        est_drop_s = VALVE_TIME_MAX + INTER_PULSE_INTERVAL
        est_duration_s = (
            total_drops * est_drop_s + len(VALVE_TIMES_TO_TEST) * SETTLE_TIME_S
        )
        times_str = ", ".join(f"{t:.4f}s" for t in VALVE_TIMES_TO_TEST)
        logging.info(
            f"\n{'=' * 60}\n"
            f"Calibration plan\n"
            f"  Valves:        {', '.join(str(v) for v in VALVES_TO_CALIBRATE)}\n"
            f"  Opening times: {times_str}\n"
            f"  N drops/point: {N_DROPS} (fixed)\n"
            f"  Settle time:   {SETTLE_TIME_S} s\n"
            f"  Conditions:    {len(VALVES_TO_CALIBRATE)} valves × {len(VALVE_TIMES_TO_TEST)} times = {n_conditions}\n"
            f"  Total drops:   {total_drops}\n"
            f"  Est. duration: ~{est_duration_s / 60:.0f} min\n"
            f"{'=' * 60}"
        )

        random_valve_times = VALVE_TIMES_TO_TEST.copy()
        random.shuffle(random_valve_times)

        scale = self.input_kwargs.get("scale") or make_scale(
            serial_port=self.input_kwargs.get("serial_port_scale", ""),
        )
        scale.start()
        scale.tare()
        logging.info(f"Scale ready. Post-tare: {scale.read_weight_blocking():.4f} g")

        calibration = CalibrationDataWater(
            file_path=self.input_kwargs["calibration_file_water"]
        )

        for valve_id in VALVES_TO_CALIBRATE:
            valve_times_measured: list[float] = []
            valve_ul_measured: list[float] = []

            for valve_opening_time in random_valve_times:
                logging.info(
                    f"Valve {valve_id} | open={valve_opening_time:.4f}s | {N_DROPS} drops"
                )

                scale.tare()
                weight_before = scale.read_weight_blocking()

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

                time.sleep(SETTLE_TIME_S)
                weight_after = scale.read_weight_blocking()

                water_weight_g = round(weight_after - weight_before, PRECISION_DECIMALS)
                ul_per_drop = round(water_weight_g * 1000 / N_DROPS, 3)
                logging.info(
                    f"Valve {valve_id} | open={valve_opening_time:.4f}s | "
                    f"weight={water_weight_g:.4f}g | {ul_per_drop:.3f} µL/drop"
                )

                valve_times_measured.append(valve_opening_time)
                valve_ul_measured.append(ul_per_drop)

                calibration.add_calibration_point(
                    valve_id=valve_id,
                    valve_opening_time=valve_opening_time,
                    n_drops=N_DROPS,
                    inter_pulse_interval=INTER_PULSE_INTERVAL,
                    water_weight_g=water_weight_g,
                )

            # --- Per-valve outlier check ---
            if len(valve_times_measured) >= 3:
                outlier_mask, residuals = flag_outlier_points(
                    valve_times_measured, valve_ul_measured, OUTLIER_SIGMA
                )
                sigma_val = float(np.std(residuals)) or 1.0
                if outlier_mask.any():
                    logging.warning(
                        f"Valve {valve_id}: {int(outlier_mask.sum())} outlier(s) detected:"
                    )
                    for i, (is_out, t, ul, res) in enumerate(
                        zip(
                            outlier_mask,
                            valve_times_measured,
                            valve_ul_measured,
                            residuals,
                        )
                    ):
                        if is_out:
                            logging.warning(
                                f"  open_s={t:.4f}s | {ul:.3f} µL/drop | "
                                f"residual={res:+.3f} µL ({abs(res) / sigma_val:.1f}σ) — consider repeating"
                            )
                else:
                    logging.info(
                        f"Valve {valve_id}: no outliers detected ({OUTLIER_SIGMA}σ threshold)."
                    )

        logging.debug(f"\n{str(calibration)}\n")
        calibration.save(overwrite=True)
        calibration.save_calibration_plot()

        if config_dir and setup_name and not setup_name.startswith("unknown_"):
            for valve_id in VALVES_TO_CALIBRATE:
                try:
                    new_cal = calibration.to_valve_calibration(valve_id)
                except ValueError as e:
                    logging.warning(
                        f"Valve {valve_id}: cannot build ValveCalibration — {e}"
                    )
                    continue

                is_valid, reason = new_cal.validate()
                logging.info(
                    f"Valve {valve_id}: validation {'PASS' if is_valid else 'FAIL'} — {reason}"
                )
                written = update_valve_calibration(
                    config_dir=config_dir,
                    setup_name=setup_name,
                    valve_id=valve_id,
                    new_calibration=new_cal,
                    force=force_save,
                )
                if written:
                    logging.info(
                        f"Valve {valve_id}: written to {setup_name}.yaml "
                        f"({len(new_cal.points)} points, updated {new_cal.updated})"
                    )
                else:
                    logging.warning(
                        f"Valve {valve_id}: NOT written — validation failed. "
                        "Re-run with force_save_calibration=true to override."
                    )
        else:
            logging.info(
                "No --setup name provided; calibration saved to CSV only. "
                "Pass --setup <name> to also update the setup YAML."
            )


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        logging.info("Calibration task complete.")


if __name__ == "__main__":
    run_task()
