import logging
import time
from multiprocessing import Queue
from pathlib import Path

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from rpi_camera_colony.control.conductor import Conductor

from murine_shift_work import settings
from murine_shift_work.logic.task_process import parse_task_args
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner
from murine_shift_work.tasks.probabilistic_switching.online_plotting import (
    OnlinePlottingForPS,
)


class Task(TaskRunner):
    def run(self):
        trial_index = 0
        max_trials = 4
        while self.continue_task and trial_index < max_trials:
            print(f"Trial {trial_index}")

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
                self.input_kwargs["objects"]["kill_queue"]
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

        self.kill_queue.put(True)
        logging.debug("Exiting Task.")


def run_task(is_cli_call=True, testing=False):
    args_dict = parse_task_args(is_cli_call=is_cli_call, testing=testing)
    args_dict.update({"task": "video"})
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
    with TaskProcess(**args_dict) as tp:
        camera_config_file = Path(settings.__file__).parent / "camera.rcc.config"
        conductor_args = {
            "config_file": str(camera_config_file),
            "acquisition_name": tp.session_paths["session_basename"],
        }
        c = Conductor(**conductor_args)
        c.start_acquisition()

        plotting_process = OnlinePlottingForPS(
            session_name="x",
            is_simulation=False,
            data_queue=dq,
            kill_queue=kq,
        )
        plotting_process.start()

        time.sleep(5)
        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        kq.put(True)
        c.stop_acquisition()
        c.cleanup()
        time.sleep(1)


if __name__ == "__main__":
    run_task(testing=True)
    print("main")
