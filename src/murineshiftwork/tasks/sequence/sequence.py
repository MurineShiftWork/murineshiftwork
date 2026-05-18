import logging
import time
from multiprocessing import Queue

from pybpodapi.state_machine import StateMachine
from ttl_barcoder.core.barcode_ttl import BarcodeTTL

from murineshiftwork.logic.barcode import (
    barcode_config_from_settings,
    inject_barcode_states,
    prepare_barcode,
)
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner
from murineshiftwork.tasks.sequence.online_plotting import OnlinePlottingForSA
from murineshiftwork.tasks.sequence.task_objects import TaskControl


class Task(TaskRunner):
    def run(self):
        task_settings = self.input_kwargs["settings.task.patched"]

        # Inject top-level kwargs that task_objects needs (calibration_file_water
        # comes via settings.task.patched from evaluate.py — no manual injection needed)
        task_settings["subject"] = self.input_kwargs.get("subject", "unknown")
        task_settings.setdefault(
            "session_paths", self.input_kwargs.get("session_paths", {})
        )

        barcode_cfg = barcode_config_from_settings(task_settings)
        barcoder = BarcodeTTL(barcode_cfg)
        bnc_channel = getattr(
            self.bpod.OutputChannels,
            f"BNC{task_settings['HARDWARE_BNC_TRIAL_START']}",
        )

        task_control = TaskControl(bpod=self.bpod, task_settings=task_settings)
        self.bpod.softcode_handler_function = task_control.softcode_handler

        trial_index = 0
        max_trials = task_settings["n_max_trials"]

        while self.continue_task and trial_index < max_trials:
            logging.info(f"Trial: {trial_index}")

            barcode_value = None
            barcode_wall_time = None

            if trial_index == 0 and not task_settings["testing"]:
                barcode_value, barcode_wall_time, timing_seq = prepare_barcode(barcoder)
                sma = StateMachine(bpod=self.bpod)
                sma = inject_barcode_states(
                    sma, timing_seq, bnc_channel, last_state_name="exit"
                )
            else:
                sma = task_control.draw_next_trial()

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(f"No data on trial #{trial_index}. Terminating.")
                self.input_kwargs["objects"]["kill_queue"].put(True)
                break

            trial_data = self.bpod.session.current_trial.export()
            task_control.update(
                trial_index=trial_index,
                trial_data=trial_data,
                barcode_value=barcode_value,
                barcode_wall_time=barcode_wall_time,
            )
            task_control.save()

            if task_settings.get("show_live_plot", True) and trial_index > 0:
                info = trial_data.get("info", {})
                if info.get("trial_type") == "task":
                    self.input_kwargs["objects"]["data_queue"].put(
                        {
                            "trial_index": task_control.trial_index,
                            "outcome": task_control.last_outcome,
                            "level": task_control.current_level,
                            "perf_buffer_mean": info.get("perf_buffer_mean", 0.0),
                        }
                    )

            trial_index += 1

        # Session-end barcode: fires after last trial completes (including on Ctrl+C stop),
        # before Bpod closes. Provides a second alignment anchor for clock-drift correction.
        if not task_settings["testing"]:
            try:
                bv_end, bwt_end, timing_seq_end = prepare_barcode(barcoder)
                sma_end = StateMachine(bpod=self.bpod)
                sma_end = inject_barcode_states(
                    sma_end,
                    timing_seq_end,
                    bnc_channel,
                    last_state_name="exit",
                )
                self.bpod.send_state_machine(sma_end)
                self.bpod.run_state_machine(sma_end)
                trial_data_end = self.bpod.session.current_trial.export()
                task_control.update(
                    trial_index=trial_index,
                    trial_data=trial_data_end,
                    barcode_value=bv_end,
                    barcode_wall_time=bwt_end,
                )
                task_control.save()
                logging.info("Session-end barcode sent.")
            except Exception:
                logging.warning("Session-end barcode failed to send.", exc_info=True)

        task_control.save_session_end()
        self.input_kwargs["objects"]["kill_queue"].put(True)
        logging.debug("Exiting Task.")


def run_task(**args_dict):
    """Entry point called by the MSW CLI: ``msw run -s <subject> -t sequence``."""
    dq: Queue = Queue()
    kq: Queue = Queue()
    args_dict.update({"objects": {"data_queue": dq, "kill_queue": kq}})
    args_dict.update({"auto_start": False})

    task_settings = args_dict.get("settings.task.patched", {})

    with TaskProcess(**args_dict) as tp:
        # Online plot (separate process)
        if task_settings.get("show_live_plot", True):
            plotting = OnlinePlottingForSA(
                session_name=tp.session_paths.get("session_basename", ""),
                data_queue=dq,
                kill_queue=kq,
                n_max_trials=task_settings.get("n_max_trials", 1500),
                n_levels=50,
                progression_threshold=task_settings.get("progression_threshold", 0.9),
                progression_threshold_advanced=task_settings.get(
                    "progression_threshold_advanced", 0.8
                ),
                regression_threshold=task_settings.get("regression_threshold", 0.2),
            )
            plotting.start()

        time.sleep(1)

        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        kq.put(True)
        time.sleep(1)


if __name__ == "__main__":
    run_task()
