import logging
import time

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine

from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


class Task(TaskRunner):
    def run(self):
        valve_opening_time = 2
        valve_numbers = [1, 2, 3, 4]

        valves_to_open = []
        for valve in valve_numbers:
            # FIXME: check that codes 1,2,3,4 work and not requird to use 1,2,4,8
            valves_to_open.append((Bpod.OutputChannels.Valve, valve))

        sma = StateMachine(bpod=self.bpod)
        sma.add_state(
            state_name="drop_it_like_its_water",
            state_timer=valve_opening_time,
            state_change_conditions={Bpod.Events.Tup: "exit"},
            output_actions=valves_to_open,
        )

        self.bpod.send_state_machine(sma)

        if not self.bpod.run_state_machine(sma):
            logging.debug("No data returned")


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
