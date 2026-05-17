import logging
import time
from pathlib import Path

import numpy as np

from murineshiftwork.hardware.bpod.ttl import make_ttl_identifier_sequences
from murineshiftwork.logic.io import save_trial_data
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


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
        save_trial_data(self.data, str(save_path) + ".df.jsonl")
        logging.debug(f"Saved data in {np.round(time.time() - dt, 2)}s.")


class Task(TaskRunner):
    def run(self) -> None:
        bnc_channels_to_test = [1, 2]
        test_sequence = "LLssLLss"

        save_path = Path(self.bpod.workspace_path) / self.bpod.session_name
        task_data = TaskData(save_path=save_path)

        for trial_index, bnc_channel in enumerate(bnc_channels_to_test):
            logging.info(
                f"Testing BNC outputs with TTL sequence {test_sequence} on BNC channel {bnc_channel}"
            )
            sma = make_ttl_identifier_sequences(
                bpod=self.bpod,
                sequence=test_sequence,
                output_chanel_pulse=eval(f"Bpod.OutputChannels.BNC{bnc_channel}"),
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


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
