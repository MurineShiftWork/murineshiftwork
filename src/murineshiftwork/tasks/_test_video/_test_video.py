import logging
import time
from multiprocessing import Queue

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from rpi_camera_colony.control.conductor import Conductor

from murineshiftwork.hardware.bpod.ttl import make_ttl_identifier_sequences
from murineshiftwork.logic.task_process import TaskProcess
from murineshiftwork.logic.task_process import TaskRunner
from murineshiftwork.tasks.probabilistic_switching.online_plotting import (
    OnlinePlottingForPS,
)


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
    # Make objects
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

    # Do not auto start, so that camera can start first
    args_dict.update({"auto_start": False})

    # Enter behaviour context
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

        # Online plotting
        plotting_process = OnlinePlottingForPS(
            session_name="x",
            is_simulation=False,
            data_queue=dq,
            kill_queue=kq,
        )
        plotting_process.start()

        # Delay for video to start
        time.sleep(5)

        # Start task
        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                kq.put(True)
                tp.stop_task()

        # Stop online plotting
        kq.put(True)

        # Stop video
        c.stop_acquisition()
        c.cleanup()

        time.sleep(1)


if __name__ == "__main__":
    print("main")
