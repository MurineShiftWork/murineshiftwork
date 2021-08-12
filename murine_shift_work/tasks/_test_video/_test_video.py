import logging
import time
from multiprocessing import Queue
from pathlib import Path

from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from rpi_camera_colony.control.process_sandbox import ConductorAsProcess

from murine_shift_work import settings
from murine_shift_work.logic.task_process import parse_task_args
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


class Task(TaskRunner):
    def prepare(self):
        self.kill_queue = Queue()
        self.camera_config_file = Path(settings.__file__).parent / "camera.config"
        self.conductor_args = {
            "config_file": str(self.camera_config_file),
            "acquisition_name": self.bpod.session_name,
        }
        self.video_process = ConductorAsProcess(
            conductor_args=self.conductor_args, kill_queue=self.kill_queue
        )
        time.sleep(1)
        self.video_process.start()
        time.sleep(8)

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
                self.kill_queue.put(True)
                break

            trial_index += 1

        self.kill_queue.put(True)
        self.video_process.join(1)


def run_task():
    # FIXME: instead of parsing from command line, find task settings.config in task dicts
    args_dict = parse_task_args()

    # Update variables here for GUI call:
    # -> Set called_from_command to False if is called from GUI
    # args_dict.update({"called_from_command": False})
    # -> get_subject_from_pybpod_conf
    # from murine_shift_work.logic.paths import get_subject_from_pybpod_conf
    # subject = get_subject_from_pybpod_conf()
    args_dict.update({"task": "video"})

    with TaskProcess(**args_dict) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


run_task()

if __name__ == "__main__":
    print("main")
