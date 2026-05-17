import logging
import time

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine

from murineshiftwork.hardware.bpod.ttl import (
    add_trial_onset_ttl,
    make_ttl_identifier_sequences,
)
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1

    def run(self) -> None:
        TTL_IDENTIFIER_SEQUENCE = ""
        TRIGGER_ITI = 5  # seconds

        trial_index = 0
        n_max_trials = 15000
        while self.continue_task and trial_index <= n_max_trials:
            logging.info(
                f"Executing trial {trial_index} [Runtime: {np.round(trial_index * TRIGGER_ITI / 60, 3)}min]"
            )

            if trial_index == 0:
                sma = make_ttl_identifier_sequences(
                    bpod=self.bpod,
                    sequence=TTL_IDENTIFIER_SEQUENCE,
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
                    state_timer=TRIGGER_ITI,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[],
                )

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                break

            trial_index += 1


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
