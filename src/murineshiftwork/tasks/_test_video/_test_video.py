import logging
import time
from multiprocessing import Queue
from pathlib import Path

import numpy as np
from pybpodapi.protocol import Bpod, StateMachine
from rpi_camera_ensemble.conductor.conductor import Conductor
from rpi_camera_ensemble.config.acquisition import EnsembleAcquisitionConfig
from rpi_camera_ensemble.config.conductor import ConductorConfig

from murineshiftwork.hardware.bpod.ttl import make_ttl_identifier_sequences
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class Task(TaskRunner):
    def run(self):
        sma = make_ttl_identifier_sequences(
            bpod=self.bpod,
            sequence="LsLsLs",
            output_chanel_pulse=eval("Bpod.OutputChannels.BNC1"),
        )
        self.bpod.run_state_machine(sma)
        logging.info("Protocol sequence sent.")

        trial_index = 0
        max_trials = 4
        while self.continue_task and trial_index < max_trials:
            logging.info(f"Trial {trial_index}")

            sma = StateMachine(bpod=self.bpod)
            sma.add_state(
                state_name="test_state_1",
                state_timer=1,
                state_change_conditions={Bpod.Events.Tup: "test_state_2"},
                output_actions=[],
            )
            sma.add_state(
                state_name="test_state_2",
                state_timer=1,
                state_change_conditions={Bpod.Events.Tup: "exit"},
                output_actions=[],
            )
            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning("No data returned.")
                self.input_kwargs["objects"]["kill_queue"].put(True)
                break

            self.input_kwargs["objects"]["data_queue"].put(
                {
                    "trial_index": trial_index,
                    "moving_average": np.random.randint(0, 1),
                    "block_probability_left": 1,
                    "block_probability_right": 0.35,
                    "choice": np.random.randint(-1, 1),
                    "rewarded": 0,
                    "was_stop": 0,
                    "punished": 0,
                }
            )

            trial_index += 1

        self.input_kwargs["objects"]["kill_queue"].put(True)
        logging.debug("Exiting Task.")


def run_task(**args_dict):
    """Task: test video."""
    dq = Queue()
    kq = Queue()
    args_dict.update(
        {
            "objects": {
                "data_queue": dq,
                "kill_queue": kq,
            },
        },
    )
    args_dict.update({"auto_start": False})

    ensemble_cfg_file = args_dict["config_file_camera"]
    assert Path(ensemble_cfg_file).exists(), (
        f"Camera config not found: {ensemble_cfg_file}"
    )
    ensemble_cfg = EnsembleAcquisitionConfig.from_yaml(path=ensemble_cfg_file)
    conductor_cfg = ConductorConfig(data_dir=args_dict.get("out_path"))
    conductor = Conductor(config=conductor_cfg, ensemble_config=ensemble_cfg)
    conductor.start()
    conductor.setup_agents()

    with TaskProcess(**args_dict) as tp:
        conductor.initialize_acquisition(
            acquisition_path=tp.session_paths["session_folder_relative"],
            acquisition_name=tp.session_paths["session_basename"],
        )
        conductor.start_preview()
        conductor.start_recording()

        time.sleep(5)

        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                kq.put(True)
                tp.stop_task()

        conductor.stop_acquisition()
        conductor.stop()

        time.sleep(1)


if __name__ == "__main__":
    print("main")
