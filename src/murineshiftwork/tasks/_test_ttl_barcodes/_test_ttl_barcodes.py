import logging
import time

import numpy as np
from pybpodapi.state_machine import StateMachine

from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    BarcodeConfig,
    BarcodeTTL,
    inject_barcode_states,
)
from murineshiftwork.logic.io import save_trial_data
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class TaskData:
    save_path = None
    data: list = []

    def __init__(self, save_path=None):
        super().__init__()
        self.save_path = save_path

    def append(self, trial_index=None, trial_data=None, **info_dict_extension):
        first_state_name = str(list(trial_data["States timestamps"].keys())[0]).lower()
        trial_type = (
            "barcode"
            if first_state_name == BARCODE_FIRST_STATE_NAME.lower()
            else "task"
        )
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
        save_trial_data(self.data, str(save_path))
        logging.debug(f"Saved data in {np.round(time.time() - dt, 2)}s.")


class Task(TaskRunner):
    def run(self) -> None:
        bnc_channels_to_test = [1, 2]
        task_data = TaskData(save_path=self.get_path("df.jsonl"))
        barcoder = BarcodeTTL(BarcodeConfig.default())

        for trial_index, bnc_channel in enumerate(bnc_channels_to_test):
            logging.info(f"Sending TTL barcode on BNC channel {bnc_channel}")
            _, _, timing_seq = barcoder.prepare()
            sma = StateMachine(bpod=self.bpod)
            sma = inject_barcode_states(
                sma,
                timing_seq,
                getattr(self.bpod.OutputChannels, f"BNC{bnc_channel}"),
                last_state_name="exit",
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
