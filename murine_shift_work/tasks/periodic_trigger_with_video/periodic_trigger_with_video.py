import logging
import time

from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine
from rpi_camera_colony.control.conductor import Conductor

from murine_shift_work.logic.specific_state_machines import add_trial_onset_ttl
from murine_shift_work.logic.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner
from murine_shift_work.settings import get_ttl_identifier_sequence


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1

    def run(self) -> None:

        TTL_IDENTIFIER_SEQUENCE = get_ttl_identifier_sequence(__file__)
        TRIGGER_ITI = 5  # seconds

        trial_index = 0
        n_max_trials = 1500
        while self.continue_task and trial_index <= n_max_trials:
            logging.info(f"Executing trial {trial_index}")

            if trial_index == 0:
                sma = make_protocol_identifier_ttl_sequence(
                    bpod=self.bpod,
                    sequence=TTL_IDENTIFIER_SEQUENCE,
                    output_chanel_pulse=self._bnc_channel_trial_onset,
                )
            else:
                sma = StateMachine(bpod=self.bpod)
                # Trial onset == main event of this convenience task
                sma = add_trial_onset_ttl(
                    sma=sma,
                    ttl_pulse_duration=0.001,
                    bnc_channel=self._bnc_channel_trial_onset,
                    next_state="iti",
                )

                sma.add_state(
                    state_name="iti",
                    state_timer=TRIGGER_ITI,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[],
                )

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                break


def run_task(**args_dict):

    # Do not auto start, so that camera can start first
    args_dict.update({"auto_start": False})

    with TaskProcess(**args_dict) as tp:
        # Video
        group = tp.session_paths["session_basename"].split("__")[0]
        conductor_args = {
            "config_file": args_dict["config_file_camera"],
            "acquisition_group": group,
            "acquisition_name": tp.session_paths["session_basename"],
        }
        c = Conductor(**conductor_args)
        c.start_acquisition()

        # Delay for video to start
        time.sleep(5)

        # Start task
        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

    # Stop video
    c.stop_acquisition()
    c.cleanup()

    time.sleep(1)


if __name__ == "__main__":
    print("main")
