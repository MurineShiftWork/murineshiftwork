# Two-armed bandit task for head-fixed setup with retractable spouts.
"""
TODO

- [ ] API for actuators
- [ ] state machine without center port
- [ ] spout evaluation + movement in separate routine to sort out before protocol starts (VIDEO ??)
- [ ] approach/retract spout during paradigm
- [ ] expose state change event for changing between port/bnc for spout events
- [ ] record video as in PS Task
- [ ]

HELPER TASK
- save known positions for stage:
    "front"(x,y,z) is only unknown per subject,
    "back" can be same -y position without changing x/z

TASK STRUCTURE

    stage approaches
    wait for choice
        response -> reward or nothing -> DELAY ?? -> retract spouts
        timeout -> retract spouts
    ITI with retracted spouts


"""

import contextlib
import logging
import time
from multiprocessing import Queue

from pybpodapi.state_machine import StateMachine

from murineshiftwork.logic.barcode import (
    BarcodeTTL,
    barcode_config_from_settings,
    inject_barcode_states,
)
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner
from murineshiftwork.tasks.probabilistic_switching_fixedsubjects.online_plotting import (
    OnlinePlottingForPS,
)
from murineshiftwork.tasks.probabilistic_switching_fixedsubjects.task_objects import (
    TaskControl,
)


class Task(TaskRunner):
    def run(self):
        task_settings = self.input_kwargs["settings.task.patched"]

        barcode_cfg = barcode_config_from_settings(task_settings)
        barcoder = BarcodeTTL(barcode_cfg)
        bnc_channel = getattr(
            self.bpod.OutputChannels,
            f"BNC{task_settings['HARDWARE_BNC_TRIAL_START']}",
        )

        session_file_path = self.input_kwargs.get("session_paths", {}).get(
            "session_file_path", ""
        )
        task_control = TaskControl(
            bpod=self.bpod,
            task_settings=task_settings,
            barcoder=barcoder,
            save_path_data=session_file_path or None,
        )
        self.bpod.softcode_handler_function = task_control.softcode_handler

        trial_index = 0
        max_trials = task_settings["n_max_trials"]
        while self.continue_task and trial_index < max_trials:
            logging.info(f"Trial: {trial_index}")

            barcode_value = None
            barcode_wall_time = None

            if trial_index == 0 and not task_settings["testing"]:
                barcode_value, barcode_wall_time, timing_seq = barcoder.prepare()
                sma = StateMachine(bpod=self.bpod)
                sma = inject_barcode_states(
                    sma, timing_seq, bnc_channel, last_state_name="exit"
                )
            else:
                sma = task_control.draw_next_trial()

            try:
                self.bpod.send_state_machine(sma)
                has_run = self.bpod.run_state_machine(sma)
            except TypeError:
                has_run = False
            except OSError as exc:
                logging.error(
                    f"Bpod serial connection lost on trial #{trial_index}"
                    f" — USB I/O error: {exc}"
                )
                self.input_kwargs["objects"]["kill_queue"].put(True)
                break

            if not has_run:
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                trial_index += 1

            trial_data = self.bpod.session.current_trial.export()
            task_control.update(
                trial_index=trial_index,
                trial_data=trial_data,
                barcode_value=barcode_value,
                barcode_wall_time=barcode_wall_time,
            )
            if task_settings["show_live_plot"] and trial_index > 0:
                self.input_kwargs["objects"]["data_queue"].put(
                    {
                        "trial_index": task_control.trial_index,
                        "moving_average": task_control.moving_average.avg,
                        "block_probability_left": task_control.probability_left,
                        "block_probability_right": task_control.probability_right,
                        "choice": task_control.last_choice,
                        "rewarded": task_control.last_rewarded,
                        "was_stop": task_control.last_stop,
                        "punished": task_control.last_punish,
                        "forced_choice": task_control.last_forced_choice,
                    }
                )

            task_control.save()
            trial_index += 1

        if not task_settings["testing"]:
            try:
                bv_end, bwt_end, timing_seq_end = barcoder.prepare()
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

        self.input_kwargs["objects"]["kill_queue"].put(True)
        logging.debug("Exiting Task.")


def run_task(**args_dict):
    """Task: PS fixed."""
    dq = Queue()
    kq = Queue()
    args_dict.update({"objects": {"data_queue": dq, "kill_queue": kq}})
    args_dict.update({"auto_start": False})

    setup_name = args_dict.get("metadata", {}).get("setup", "")
    _subject = args_dict.get("subject", "")

    # Camera setup — optional: fall back to no-video if config missing or agents unreachable
    from murineshiftwork.hardware.camera.client import make_camera_client

    conductor = make_camera_client(
        cameras_config=args_dict.get("cameras_config"),
        config_file_camera=args_dict.get("config_file_camera", ""),
        output_dir=args_dict.get("out_path", ""),
    )
    if conductor is not None:
        conductor.start()
        try:
            conductor.setup_agents()
        except ConnectionError as exc:
            logging.warning(f"Camera agents unreachable — running without video: {exc}")
            with contextlib.suppress(Exception):
                conductor.stop()
            conductor = None
    else:
        logging.info("No camera config — running without video.")

    try:
        with TaskProcess(**args_dict) as tp:
            if conductor is not None:
                conductor.initialize_acquisition(
                    acquisition_path=tp.session_paths["session_folder_relative"],
                    acquisition_name=tp.session_paths["session_basename"],
                )
                conductor.start_preview()
                conductor.start_recording()
                time.sleep(3)

            _setup_str = f"[{setup_name}] " if setup_name else ""
            plotting_process = OnlinePlottingForPS(
                window_title=f"{_setup_str}{_subject} @ probabilistic_switching_fixedsubjects",
                is_simulation=False,
                data_queue=dq,
                kill_queue=kq,
            )
            plotting_process.start()

            tp.run_task()
            while tp.is_running():
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    tp.stop_task()

            kq.put(True)
            if conductor is not None:
                try:
                    conductor.stop_acquisition()
                except Exception as _exc:
                    logging.warning(
                        f"conductor.stop_acquisition() did not complete cleanly: {_exc}"
                    )
    finally:
        if conductor is not None:
            with contextlib.suppress(Exception):
                conductor.stop()
        time.sleep(1)


if __name__ == "__main__":
    run_task()
    print("main")
