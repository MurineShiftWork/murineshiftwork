import logging
import time

import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_ttl_identifier_sequences,
)
from murine_shift_work.logic.stimulation import Stimulation
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


class OptoTagging(object):
    input_kwargs = {}
    out_path = ""

    trial_data = []

    def __init__(self, out_path=None, **kwargs):
        self.out_path = out_path
        self.input_kwargs = kwargs

    def update(self, trial_index=None, trial_data=None):
        first_state_name = str(list(trial_data["States timestamps"].keys())[0]).lower()
        if trial_index < 1 and first_state_name.startswith("pulse"):
            # IF TTL TRIAL
            trial_data["info"] = {"trial_type": "ttl", "trial_index": trial_index}
            return self.trial_data.append(trial_data)
        else:
            trial_data["info"] = {"trial_type": "task", "trial_index": trial_index}
            return self.trial_data.append(trial_data)

    def save(self):
        session_df = pd.DataFrame(self.trial_data)
        session_df.to_pickle(str(self.out_path) + ".msw.pkl")
        logging.debug(f"Saved session data to {str(self.out_path)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def __del__(self):
        self.save()


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1
    _bnc_channel_stimulation = Bpod.OutputChannels.BNC2

    def run(self) -> None:
        task_settings = self.input_kwargs["settings.task.patched"]
        serial_port_pulsepal = self.input_kwargs.get(
            "serial_port_pulsepal", task_settings["hardware"]["serial_port_pulsepal"]
        )
        stimulation = Stimulation(
            port=serial_port_pulsepal,
            in_dict=task_settings["stimulation"],
        )
        stimulation.connect()
        pulse_train_duration = task_settings["stimulation"]["pulse_train_duration"]

        optotagging = OptoTagging(
            out_path=self.input_kwargs["session_paths"]["session_file_path"]
        )

        trial_index = 0
        while self.continue_task and trial_index <= task_settings["N_MAX_TRIALS"]:
            logging.info(f"Executing trial {trial_index}")

            if trial_index == 0:
                sma = make_ttl_identifier_sequences(
                    bpod=self.bpod,
                    sequence=task_settings["TTL_IDENTIFIER_SEQUENCE"],
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
                    state_timer=task_settings["TRIGGER_ITI"],  # + pulse_train_duration,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[],
                )

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                break

            trial_data = self.bpod.session.current_trial.export()
            optotagging.update(trial_index=trial_index, trial_data=trial_data)
            optotagging.save()
            trial_index += 1

        logging.debug("Exiting Task.")


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
