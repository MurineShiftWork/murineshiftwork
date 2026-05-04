import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
# from rpi_camera_colony.control.conductor import Conductor
from rpi_camera_ensemble.conductor.conductor import Conductor
from rpi_camera_ensemble.config.acquisition import (
    EnsembleAcquisitionConfig,
)
from rpi_camera_ensemble.config.conductor import ConductorConfig

from murine_shift_work.io.trial_data import save_trial_data
from murine_shift_work.logic.misc import draw_jittered_trial_time
from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_ttl_identifier_sequences,
)
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


class AirPuff(object):
    input_kwargs = {}
    out_path = ""

    trial_data = []

    def __init__(self, out_path=None, **kwargs):
        self.out_path = out_path
        self.input_kwargs = kwargs

    def update(
        self,
        trial_index=None,
        air_puff_duration=None,
        iti_this_trial=None,
        trial_data=None,
    ):
        first_state_name = str(
            list(trial_data["States timestamps"].keys())[0]
        ).lower()
        trial_type = (
            "ttl"
            if trial_index < 1 and first_state_name.startswith("pulse")
            else "task"
        )
        trial_data["info"] = {
            "trial_type": trial_type,
            "trial_index": trial_index,
            "air_puff_duration": air_puff_duration,
            "iti_this_trial": iti_this_trial,
        }
        return self.trial_data.append(trial_data)

    def save(self):
        save_trial_data(self.trial_data, str(self.out_path) + ".msw.jsonl")
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

        air_puff_durations = task_settings.get("air_puff_durations")
        n_repeats_per_duration = task_settings.get("n_repeats_per_duration")
        inter_trial_interval = task_settings.get("inter_trial_interval")
        TTL_IDENTIFIER_SEQUENCE = task_settings.get("TTL_IDENTIFIER_SEQUENCE")
        HARDWARE_VALVE_FOR_AIR = task_settings.get("HARDWARE_VALVE_FOR_AIR")

        if (
            not air_puff_durations
            or not n_repeats_per_duration
            or not inter_trial_interval
            or not TTL_IDENTIFIER_SEQUENCE
        ):
            raise ValueError(
                [
                    air_puff_durations,
                    n_repeats_per_duration,
                    inter_trial_interval,
                    TTL_IDENTIFIER_SEQUENCE,
                ]
            )

        # Prepare
        _trial_types = np.asarray(
            [[dur] * n_repeats_per_duration for dur in air_puff_durations]
        )
        trial_types = np.random.permutation(_trial_types.flatten())

        air_puff_protocol = AirPuff(
            out_path=self.input_kwargs["session_paths"]["session_file_path"]
        )

        # Run
        trial_index = 0
        while self.continue_task and trial_index <= len(trial_types):
            logging.info(f"Executing trial {trial_index}")

            if trial_index == 0:
                air_puff_duration = None
                iti_this_trial = None

                sma = make_ttl_identifier_sequences(
                    bpod=self.bpod,
                    sequence=TTL_IDENTIFIER_SEQUENCE,
                    output_chanel_pulse=self._bnc_channel_trial_onset,
                )

            else:
                air_puff_duration = trial_types[trial_index - 1]
                iti_this_trial = draw_jittered_trial_time(
                    *inter_trial_interval
                )

                sma = StateMachine(bpod=self.bpod)
                # Trial onset
                sma = add_trial_onset_ttl(
                    sma=sma,
                    ttl_pulse_duration=0.001,
                    bnc_channel=self._bnc_channel_trial_onset,
                    next_state="release_puff",
                )
                # Puff TTL
                sma.add_state(
                    state_name="release_puff",
                    state_timer=air_puff_duration,
                    state_change_conditions={Bpod.Events.Tup: "iti"},
                    output_actions=[
                        (Bpod.OutputChannels.Valve, HARDWARE_VALVE_FOR_AIR)
                    ],
                )
                sma.add_state(
                    state_name="iti",
                    state_timer=iti_this_trial,
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
            air_puff_protocol.update(
                trial_index=trial_index,
                air_puff_duration=air_puff_duration,
                iti_this_trial=iti_this_trial,
                trial_data=trial_data,
            )
            air_puff_protocol.save()
            trial_index += 1

        logging.debug("Exiting Task.")


def run_task(**args_dict):
    # Do not auto start, so that camera can start first
    args_dict.update({"auto_start": False})

    # Video
    ensemble_cfg_file = args_dict["config_file_camera"]
    print("DBG:", ensemble_cfg_file)
    assert Path(ensemble_cfg_file).exists()
    ensemble_cfg = EnsembleAcquisitionConfig.from_yaml(path=ensemble_cfg_file)
    conductor_cfg = ConductorConfig(data_dir=args_dict.get("out_path", None))
    conductor = Conductor(config=conductor_cfg, ensemble_config=ensemble_cfg)
    conductor.start()
    conductor.setup_agents()

    # Enter behaviour context
    with TaskProcess(**args_dict) as tp:
        # Paths for video
        _session = tp.session_paths["session_basename"]
        _subject = tp.session_paths["subject"]

        conductor.initialize_acquisition(
            acquisition_path=(
                f"{_subject}/{args_dict['is_child_session_to']}/{_session}"
                if args_dict["is_child_session_to"] is not None
                else f"{_subject}/{_session}"
            ),
            acquisition_name=_session,
        )
        conductor.start_preview()
        conductor.start_recording()

        # Delay for video to start
        time.sleep(3)

        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        # Stop video
        conductor.stop_acquisition()
        conductor.stop()

        time.sleep(1)


if __name__ == "__main__":
    print("main")
