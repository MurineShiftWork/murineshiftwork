import json
import logging
import time

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from pypulsepal import PulsePal as PyPulsePal

from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_ttl_identifier_sequences,
)
from murine_shift_work.logic.stimulation import Stimulation
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner
from murine_shift_work.tasks.exp_trn_spindle.param_sets import stimulation_param_sets


class ProtocolObject:
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
        skip_counter = 0
        N_MAX_TRIALS = 50000
        ITI = 10
        on_off_periods = 5 * 60  # seconds
        on_off_periods_n_trial = round(on_off_periods / ITI)

        raw_out_path = self.input_kwargs["session_paths"]["session_file_path"]
        with open(str(raw_out_path) + ".msw.stimulation.json", "w") as f:
            out_json = json.dumps(stimulation_param_sets, indent=4, sort_keys=True)
            f.write(out_json)

        protocol_data = ProtocolObject(out_path=raw_out_path)
        pulsepal = PyPulsePal(serial_port="/dev/ttyACM0")
        # Link all channels to trigger one for cameras
        [
            pulsepal.program_one_param(
                channel=r, param_name="linkTriggerChannel1", param_value=1
            )
            for r in range(4)
        ]

        # TRIALS
        trial_index = 0
        while self.continue_task and trial_index <= task_settings.get(
            "N_MAX_TRIALS", N_MAX_TRIALS
        ):
            logging.info(f"Executing trial {trial_index}")

            stim_set_id = None
            trial_stim_settings = {}

            if trial_index == 0:
                sma = make_ttl_identifier_sequences(
                    bpod=self.bpod,
                    sequence=task_settings["TTL_IDENTIFIER_SEQUENCE"],
                    output_chanel_pulse=self._bnc_channel_trial_onset,
                )
            else:
                if skip_counter >= on_off_periods_n_trial:
                    if skip_counter >= 2 * on_off_periods_n_trial:
                        skip_counter = 0
                        print("RESET skip counter to change on/off phase")
                    else:
                        print("-- in OFF phase --", skip_counter)
                        time.sleep(ITI)
                        skip_counter += 1
                        continue

                print("-- in ON phase --")

                stim_set_id = np.random.randint(
                    0, len(stimulation_param_sets), dtype=int
                )
                trial_stim_settings = stimulation_param_sets.get(stim_set_id)
                pulse_train_duration = trial_stim_settings.get("pulseTrainDuration")

                print(
                    "Trial", trial_index, "Set", stim_set_id, "Val", trial_stim_settings
                )

                # update all output channels with these settings
                for ch in range(4):
                    for (
                        stim_set_param,
                        stim_set_param_value,
                    ) in trial_stim_settings.items():
                        if not ch:
                            print("UPDATING:", stim_set_param, stim_set_param_value)

                        pulsepal.program_one_param(
                            channel=ch,
                            param_name=stim_set_param,
                            param_value=stim_set_param_value,
                        )

                # MAKE OUTER TRIAL
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
                    state_timer=ITI,  # + pulse_train_duration,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[],
                )

                skip_counter += 1

            # EXECUTE & SAVE
            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                break

            trial_data = self.bpod.session.current_trial.export()
            trial_data.update(
                {"stimulation": trial_stim_settings, "stim_set_id": stim_set_id}
            )
            protocol_data.update(trial_index=trial_index, trial_data=trial_data)
            protocol_data.save()
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
