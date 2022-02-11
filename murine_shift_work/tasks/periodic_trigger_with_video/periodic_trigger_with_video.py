import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine
from rpi_camera_colony.control.conductor import Conductor

from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_ttl_identifier_sequences,
)
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


class TaskData:
    save_path = None
    data = []

    def __init__(self, save_path=None):
        super(TaskData, self).__init__()
        self.save_path = save_path

    def append(self, trial_index=None, trial_data=None, **info_dict_extension):
        # If is TTL trial
        first_state_name = str(list(trial_data["States timestamps"].keys())[0]).lower()
        if trial_index < 1 and first_state_name.startswith("pulse"):
            trial_type = "ttl"
        else:
            trial_type = "task"
            # trial_data["info"] = {"trial_type": "ttl", "trial_index": trial_index}

        trial_data["info"] = {
            "trial_type": trial_type,
            "trial_index": trial_index,
            **info_dict_extension,
        }

        self.data.append(trial_data)

    def save(self, save_path=None):
        save_path = save_path or self.save_path
        logging.debug("Saving task control data..")
        dt = time.time()
        df = pd.DataFrame(self.data)
        df.to_pickle(str(save_path) + ".df.pkl")
        logging.debug(f"Saved data in {np.round(time.time() - dt, 2)}s.")


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1

    def run(self) -> None:

        ttl_identifier_sequence = self.input_kwargs.get(
            "ttl_identifier_sequence", "LLssss"
        )
        trigger_iti = self.input_kwargs.get("trigger_iti", 5)
        max_runtime = self.input_kwargs.get("max_runtime", 7200)
        n_max_trials = self.input_kwargs.get(
            "n_max_trials", np.ceil(max_runtime / trigger_iti)
        )
        logging.info(
            f"Using TTL '{ttl_identifier_sequence}' with ITI of {trigger_iti}s for {n_max_trials} trials."
        )

        save_path = Path(self.bpod.workspace_path) / self.bpod.session_name
        task_data = TaskData(save_path=save_path)

        trial_index = 0
        while self.continue_task and trial_index <= n_max_trials:
            logging.info(
                f"Executing trial {trial_index}/{n_max_trials} "
                f"[Runtime: {np.round(trial_index*trigger_iti/60,3)}min / {np.round(max_runtime/60,3)}min]"
            )

            if trial_index == 0:
                sma = make_ttl_identifier_sequences(
                    bpod=self.bpod,
                    sequence=ttl_identifier_sequence,
                    output_chanel_pulse=self._bnc_channel_trial_onset,
                )
            else:
                sma = StateMachine(bpod=self.bpod)
                # Trial onset == main event of this convenience task
                sma = add_trial_onset_ttl(
                    sma=sma,
                    ttl_pulse_duration=0.001,
                    bnc_channel=self._bnc_channel_trial_onset,
                    next_state="iti",
                )

                sma.add_state(
                    state_name="iti",
                    state_timer=trigger_iti,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[],
                )

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                break

            task_data.append(
                trial_index=trial_index,
                trial_data=self.bpod.session.current_trial.export(),
            )
            task_data.save()
            trial_index += 1


def run_task(**args_dict):

    # Do not auto start, so that camera can start first
    args_dict.update({"auto_start": False})

    with TaskProcess(**args_dict) as tp:
        # Video
        conductor_args = {
            "config_file": args_dict["config_file_camera"],
            "acquisition_group": args_dict["is_child_session_to"]
            if args_dict["is_child_session_to"] is not None
            else tp.session_paths["session_basename"].split("__")[0],
            "acquisition_name": tp.session_paths["session_basename"],
        }
        c = Conductor(**conductor_args)
        c.start_acquisition()

        # Delay for video to start
        time.sleep(5)

        # Start task
        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

    # Stop video
    c.stop_acquisition()
    c.cleanup()

    time.sleep(1)


if __name__ == "__main__":
    print("main")
