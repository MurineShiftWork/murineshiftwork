import logging
import time

from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from murine_shift_work.logic.task_process import parse_task_args
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


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
                self.continue_task = False
                break

            trial_index += 1


def run_task(is_cli_call=True):
    args_dict = parse_task_args(is_cli_call=is_cli_call)
    args_dict.update({"task": "minimal"})

    with TaskProcess(**args_dict) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        print("Exiting WITH")
    print("THE END")


if __name__ == "__main__":
    print("main")
