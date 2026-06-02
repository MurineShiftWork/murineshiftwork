import logging
import time

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine

from murineshiftwork.hardware.bpod.ttl import add_trial_onset_ttl
from murineshiftwork.logic.barcode import (
    BarcodeTTL,
    barcode_config_from_settings,
    inject_barcode_states,
)
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class Task(TaskRunner):
    def run(self) -> None:
        patched = self.input_kwargs.get("settings.task.patched", {})
        trigger_iti = patched.get(
            "TRIGGER_ITI", self.input_kwargs.get("trigger_iti", 5)
        )
        max_runtime = patched.get(
            "MAX_RUNTIME", self.input_kwargs.get("max_runtime", 7200)
        )
        barcode_interval_s = patched.get("BARCODE_INTERVAL_S", 60)
        bnc_ch = patched.get("HARDWARE_BNC_TRIAL_START", 1)
        bnc_channel = getattr(self.bpod.OutputChannels, f"BNC{bnc_ch}")

        n_max_trials = int(
            patched.get("N_MAX_TRIALS", self.input_kwargs.get("n_max_trials", None))
            or np.ceil(max_runtime / trigger_iti)
        )
        barcode_every_n = max(1, round(barcode_interval_s / trigger_iti))

        barcoder = BarcodeTTL(barcode_config_from_settings(patched))

        logging.info(
            f"periodic_trigger: iti={trigger_iti}s max={max_runtime}s "
            f"barcode every {barcode_every_n} trials ({barcode_interval_s}s)"
        )

        trial_index = 0
        while self.continue_task and trial_index <= n_max_trials:
            logging.info(
                f"Trial {trial_index}/{n_max_trials} "
                f"[{np.round(trial_index * trigger_iti / 60, 1)} min]"
            )

            if trial_index == 0 or trial_index % barcode_every_n == 0:
                _, _, timing_seq = barcoder.prepare()
                sma = StateMachine(bpod=self.bpod)
                sma = inject_barcode_states(
                    sma, timing_seq, bnc_channel, last_state_name="iti"
                )
                sma.add_state(
                    state_name="iti",
                    state_timer=trigger_iti,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[],
                )
            else:
                sma = StateMachine(bpod=self.bpod)
                sma = add_trial_onset_ttl(
                    sma=sma,
                    ttl_pulse_duration=0.001,
                    bnc_channel=bnc_channel,
                    next_state="iti",
                )
                sma.add_state(
                    state_name="iti",
                    state_timer=trigger_iti,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[],
                )

            try:
                self.bpod.send_state_machine(sma)
                if not self.bpod.run_state_machine(sma):
                    logging.warning(
                        f"No data returned on trial #{trial_index}. Terminating."
                    )
                    break
            except OSError as exc:
                logging.error(f"Bpod connection lost on trial #{trial_index}: {exc}")
                break

            trial_index += 1

        try:
            _, _, timing_seq_end = barcoder.prepare()
            sma_end = StateMachine(bpod=self.bpod)
            sma_end = inject_barcode_states(
                sma_end, timing_seq_end, bnc_channel, last_state_name="exit"
            )
            self.bpod.send_state_machine(sma_end)
            self.bpod.run_state_machine(sma_end)
            logging.info("Session-end barcode sent.")
        except Exception:
            logging.warning("Session-end barcode failed to send.", exc_info=True)


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
