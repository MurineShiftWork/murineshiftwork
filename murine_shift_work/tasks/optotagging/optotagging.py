import logging
import time

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)
from murine_shift_work.logic.stimulation import Stimulation
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner
from murine_shift_work.tasks.optotagging import task_settings


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1
    _bnc_channel_stimulation = Bpod.OutputChannels.BNC2

    def run(self) -> None:

        stimulation = Stimulation(
            port=task_settings.PORT,
            in_dict=task_settings.selected_preset,
        )
        stimulation.connect()
        pulse_train_duration = task_settings.selected_preset["pulse_train_duration"]

        trial_index = 0
        while self.continue_task and trial_index <= task_settings.N_MAX_TRIALS:
            print(f"Executing trial {trial_index}")

            if trial_index == 0:
                sma = make_protocol_identifier_ttl_sequence(
                    bpod=self.bpod,
                    sequence=task_settings.TTL_IDENTIFIER_SEQUENCE,
                    output_chanel_pulse=self._bnc_channel_trial_onset,
                )
            else:
                sma = StateMachine(bpod=self.bpod)
                # Trial onset
                sma = add_trial_onset_ttl(
                    sma=sma,
                    ttl_pulse_duration=0.001,
                    bnc_channel=self._bnc_channel_trial_onset,
                    next_state="pulses",
                )
                # Stimulation TTL
                sma = add_trial_onset_ttl(
                    sma=sma,
                    state_name_tuple=("pulses", "pulse_off"),
                    ttl_pulse_duration=pulse_train_duration,  # 0.001,
                    bnc_channel=self._bnc_channel_stimulation,
                    next_state="iti",
                )
                sma.add_state(
                    state_name="iti",
                    state_timer=task_settings.TRIGGER_ITI,  # + pulse_train_duration,
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

        print("Exiting TaskProcess WITH")
    print("THE END run_task")


if __name__ == "__main__":
    print("main")
