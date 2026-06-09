import logging
import time

from pybpodapi.state_machine import StateMachine

from murineshiftwork.logic.barcode import (
    BarcodeConfig,
    BarcodeTTL,
    inject_barcode_states,
)
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class Task(TaskRunner):
    def run(self) -> None:
        bnc_channels_to_test = [1, 2]
        barcoder = BarcodeTTL(BarcodeConfig.default())

        for bnc_channel in bnc_channels_to_test:
            logging.info(
                f"Testing BNC output with TTL barcode on BNC channel {bnc_channel}"
            )
            _, _, timing_seq = barcoder.prepare()
            sma = StateMachine(bpod=self.bpod)
            sma = inject_barcode_states(
                sma,
                timing_seq,
                getattr(self.bpod.OutputChannels, f"BNC{bnc_channel}"),
                last_state_name="exit",
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
