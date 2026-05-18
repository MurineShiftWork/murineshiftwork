import logging
import time
from multiprocessing import Queue
from pathlib import Path

from rpi_camera_ensemble.conductor.conductor import Conductor
from rpi_camera_ensemble.config.acquisition import EnsembleAcquisitionConfig
from rpi_camera_ensemble.config.conductor import ConductorConfig

from murineshiftwork.logic.task_process import TaskProcess, TaskRunner
from murineshiftwork.tasks.probabilistic_switching.online_plotting import (
    OnlinePlottingForPS,
)
from murineshiftwork.tasks.probabilistic_switching.task_objects import (
    TaskControl,
)


class Task(TaskRunner):
    def run(self):
        task_settings = self.input_kwargs["settings.task.patched"]
        task_control = TaskControl(bpod=self.bpod, task_settings=task_settings)
        self.bpod.softcode_handler_function = task_control.softcode_handler

        trial_index = 0
        max_trials = task_settings["n_max_trials"]
        while self.continue_task and trial_index < max_trials:
            logging.info(f"Trial: {trial_index}")

            if trial_index == 0 and not task_settings["testing"]:
                from murineshiftwork.hardware.bpod.ttl import (
                    make_ttl_identifier_sequences,
                )

                sma = make_ttl_identifier_sequences(
                    bpod=self.bpod,
                    sequence=task_settings["ttl_identifier_sequence"],
                    output_chanel_pulse=getattr(
                        self.bpod.OutputChannels,
                        f"BNC{task_settings['HARDWARE_BNC_TRIAL_START']}",
                    ),
                )
            else:
                sma = task_control.draw_next_trial()

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                self.input_kwargs["objects"]["kill_queue"].put(True)
                break

            trial_data = self.bpod.session.current_trial.export()
            task_control.update(trial_index=trial_index, trial_data=trial_data)
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
                    }
                )

            task_control.save()
            trial_index += 1

        self.input_kwargs["objects"]["kill_queue"].put(True)
        logging.debug("Exiting Task.")


def run_task(**args_dict):
    """Task: PS."""
    dq = Queue()
    kq = Queue()
    args_dict.update({"objects": {"data_queue": dq, "kill_queue": kq}})
    args_dict.update({"auto_start": False})

    task_settings = args_dict.get("settings.task.patched", {})

    with TaskProcess(**args_dict) as tp:
        # Video
        ensemble_cfg_file = args_dict.get("config_file_camera", "")
        if ensemble_cfg_file and Path(ensemble_cfg_file).exists():
            ensemble_cfg = EnsembleAcquisitionConfig.from_yaml(path=ensemble_cfg_file)
            conductor_cfg = ConductorConfig(data_dir=args_dict.get("out_path", None))
            conductor = Conductor(config=conductor_cfg, ensemble_config=ensemble_cfg)
            conductor.start()
            conductor.setup_agents()
            _session = tp.session_paths["session_basename"]
            _subject = tp.session_paths["subject"]
            conductor.initialize_acquisition(
                acquisition_path=(
                    f"{_subject}/{args_dict['is_child_session_to']}/{_session}"
                    if args_dict.get("is_child_session_to")
                    else f"{_subject}/{_session}"
                ),
                acquisition_name=_session,
            )
            conductor.start_preview()
            conductor.start_recording()
            time.sleep(3)
        else:
            conductor = None
            logging.info("No camera config — running without video.")

        # Online plotting
        if task_settings.get("show_live_plot", True):
            plotting_process = OnlinePlottingForPS(
                session_name=tp.session_paths["session_basename"],
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
            conductor.stop_acquisition()
            conductor.stop()
            time.sleep(1)


if __name__ == "__main__":
    run_task()
    print("main")
