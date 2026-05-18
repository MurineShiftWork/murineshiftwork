import logging
import time

from murineshiftwork.hardware.bpod.ttl import make_ttl_identifier_sequences
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class Task(TaskRunner):
    def run(self) -> None:
        test_sequence = "LLssLLss"

        for bnc_channel in [1, 2]:
            logging.info(
                f"Testing BNC outputs with TTL sequence {test_sequence} on BNC channel {bnc_channel}"
            )
            sma = make_ttl_identifier_sequences(
                bpod=self.bpod,
                sequence=test_sequence,
                output_chanel_pulse=getattr(
                    self.bpod.OutputChannels, f"BNC{bnc_channel}"
                ),
            )

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                print("nothing returned")


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
