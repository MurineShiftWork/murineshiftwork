import logging
import time

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine

from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class Task(TaskRunner):
    def run(self):
        s = self.input_kwargs.get("settings.task.patched", {})

        valve_opening_time_ms = float(s.get("VALVE_OPENING_TIME_MS", 50.0))
        valve_numbers = list(s.get("VALVE_NUMBERS", [1, 3]))
        n_flush_cycles = int(s.get("N_FLUSH_CYCLES", 1))
        inter_flush_interval_s = float(s.get("INTER_FLUSH_INTERVAL_S", 1.0))
        flush_sequentially = bool(s.get("FLUSH_VALVES_SEQUENTIALLY", False))

        # When sequential, divide cycle time equally across valves
        per_valve_time_ms = (
            valve_opening_time_ms / len(valve_numbers)
            if flush_sequentially
            else valve_opening_time_ms
        )

        logging.info(
            f"Flush: valves={valve_numbers}, cycle_time={valve_opening_time_ms}ms, "
            + (f"per_valve={per_valve_time_ms:.1f}ms, " if flush_sequentially else "")
            + f"cycles={n_flush_cycles}, interval={inter_flush_interval_s}s, "
            f"sequential={flush_sequentially}"
        )

        for cycle in range(n_flush_cycles):
            if not self.continue_task:
                break

            if flush_sequentially:
                for valve in valve_numbers:
                    if not self.continue_task:
                        break
                    self._flush_valves([valve], per_valve_time_ms)
                logging.info(
                    f"Flush cycle {cycle + 1}/{n_flush_cycles} done (sequential: {valve_numbers})"
                )
            else:
                self._flush_valves(valve_numbers, valve_opening_time_ms)
                logging.info(f"Flush cycle {cycle + 1}/{n_flush_cycles} done")

            if cycle < n_flush_cycles - 1:
                time.sleep(inter_flush_interval_s)

    def _flush_valves(self, valves, valve_opening_time_ms):
        output_actions = [(Bpod.OutputChannels.Valve, v) for v in valves]
        sma = StateMachine(bpod=self.bpod)
        sma.add_state(
            state_name="flush_valves",
            state_timer=valve_opening_time_ms / 1000.0,
            state_change_conditions={Bpod.Events.Tup: "exit"},
            output_actions=output_actions,
        )
        self.bpod.send_state_machine(sma)
        if not self.bpod.run_state_machine(sma):
            logging.warning("No data returned from state machine")


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    run_task()
