import logging
import time

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine

from murine_shift_work.logic.calibration import CalibrationDataSound
from murine_shift_work.logic.sounds import StereoSound
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner


class Task(TaskRunner):
    _test_bnc_in_channel = Bpod.OutputChannels.BNC1

    def run(self) -> None:
        self.sound = StereoSound(sound_device=StereoSound.default_sound_device)
        self.sound_test = self.sound.register_new_sound(
            frequency=5000, duration=0.1, amplitude=0.01
        )

        calibration_sound = CalibrationDataSound(
            file_path=self.input_kwargs["calibration_file_sound"]
        )

        self.bpod.softcode_handler_function = self.sound.execute_sound_handler

        trial_index = 0
        n_max_trials = 201
        while self.continue_task and trial_index <= n_max_trials:
            logging.debug(f"\ntrial {trial_index}")

            sma = StateMachine(bpod=self.bpod)
            sma.add_state(
                state_name="sound_and_bnc_on",
                state_timer=0.005,
                state_change_conditions={"Tup": "bnc_off"},
                output_actions=[
                    ("SoftCode", self.sound_test),
                    (self._test_bnc_in_channel, 1),
                ],
            )
            sma.add_state(
                state_name="bnc_off",
                state_timer=0.1,
                state_change_conditions={"Tup": "leave"},
                output_actions=[(self._test_bnc_in_channel, 0)],  # ("SoftCode", 99),
            )
            sma.add_state(
                state_name="leave",
                state_timer=0,
                state_change_conditions={"Tup": "exit"},
                output_actions=[("SoftCode", self.sound.sound_stop_code)],
            )

            # EXECUTE trial
            dt = time.time()
            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning("nothing returned")

            logging.debug(f"Trial took {time.time()-dt}s")

            ev = self.bpod.session.current_trial.export()["Events timestamps"]
            delay = dict(ev).get("BNC1High", -1)
            if not delay == -1:
                calibration_sound += {"trial": trial_index, "delay": delay[0]}
            else:
                logging.error(f"Did not receive TTL on trial {trial_index}")

            logging.info(f"Trial {trial_index}: Delay of {delay}s")

            trial_index += 1

        # Save new calibration data for sound offset
        calibration_sound.save()
        calibration_sound.save_calibration_plot()


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
