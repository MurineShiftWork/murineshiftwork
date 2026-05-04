import json
import logging
import time
from pathlib import Path

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
from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_ttl_identifier_sequences,
)
from murine_shift_work.logic.stimulation import Stimulation
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


class OptoTagging:
    input_kwargs = {}
    out_path = ""
    trial_data = []

    def __init__(self, out_path=None, **kwargs):
        self.out_path = out_path
        self.input_kwargs = kwargs
        self.trial_data = []

    def update(self, trial_index=None, trial_data=None):
        first_state_name = str(
            list(trial_data["States timestamps"].keys())[0]
        ).lower()
        if trial_index < 1 and first_state_name.startswith("pulse"):
            # IF TTL TRIAL
            trial_data["info"] = {
                "trial_type": "ttl",
                "trial_index": trial_index,
            }
            return self.trial_data.append(trial_data)
        else:
            trial_data["info"] = {
                "trial_type": "task",
                "trial_index": trial_index,
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
        serial_port_pulsepal = self.input_kwargs.get(
            "serial_port_pulsepal",
            task_settings["hardware"]["serial_port_pulsepal"],
        )
        stimulation = Stimulation(
            port=serial_port_pulsepal,
            in_dict=task_settings["stimulation"],
        )
        stimulation.connect()
        pulse_train_duration = task_settings["stimulation"][
            "pulse_train_duration"
        ]

        optotagging = OptoTagging(
            out_path=self.input_kwargs["session_paths"]["session_file_path"]
        )

        trial_index = 0
        try:
            while (
                self.continue_task and trial_index <= task_settings["N_MAX_TRIALS"]
            ):
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
                        state_timer=task_settings[
                            "TRIGGER_ITI"
                        ],  # + pulse_train_duration,
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
        finally:
            stimulation.disconnect()
            logging.info("Stimulation disconnected.")

        logging.debug("Exiting Task.")


def run_task(**args_dict):
    task_settings = args_dict.get("settings.task.patched")
    all_sub_task_settings = task_settings.get("stimulation")

    print(json.dumps(all_sub_task_settings, indent=4, sort_keys=True))

    for sub_task_name, sub_task_settings in all_sub_task_settings.items():
        print(
            f"\n\n\n"
            f"SUB TASK: {sub_task_name}\n{json.dumps(sub_task_settings, indent=4, sort_keys=True)}"
            f"\n\n\n"
        )
        patched_arg_dict = args_dict.copy()
        patched_arg_dict["settings.task.patched"][
            "stimulation"
        ] = sub_task_settings

        # Do not auto start, so that camera can start first
        patched_arg_dict.update({"auto_start": False})

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
        with TaskProcess(**patched_arg_dict) as tp:
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
            print(f"EXITING SUB TASK: {sub_task_name}")


if __name__ == "__main__":
    print("main")
