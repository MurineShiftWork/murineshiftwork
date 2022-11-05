# Two-armed bandit task for head-fixed setup with retractable spouts.
"""
TODO

- [ ] API for actuators
- [ ] state machine without center port
- [ ] spout evaluation + movement in separate routine to sort out before protocol starts (VIDEO ??)
- [ ] approach/retract spout during paradigm
- [ ] expose state change event for changing between port/bnc for spout events
- [ ] record video as in PS Task
- [ ]

HELPER TASK
- save known positions for stage:
    "front"(x,y,z) is only unknown per subject,
    "back" can be same -y position without changing x/z

TASK STRUCTURE

    stage approaches
    wait for choice
        response -> reward or nothing -> DELAY ?? -> retract spouts
        timeout -> retract spouts
    ITI with retracted spouts


"""
import logging
import time
from multiprocessing import Queue

from pybpodapi.protocol import Bpod  # Used!
from rpi_camera_colony.control.conductor import Conductor

from murine_shift_work.logic.specific_state_machines import (
    make_ttl_identifier_sequences,
)
from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner
from murine_shift_work.tasks.probabilistic_switching_fixedsubjects.online_plotting import (
    OnlinePlottingForPS,
)
from murine_shift_work.tasks.probabilistic_switching_fixedsubjects.task_objects import (
    TaskControl,
)


class Task(TaskRunner):
    def run(self):
        task_settings = self.input_kwargs["settings.task.patched"]
        task_settings["calibration_file_sound"] = self.input_kwargs[
            "calibration_file_sound"
        ]  # fixme: improve handing down args
        task_settings["calibration_file_water"] = self.input_kwargs[
            "calibration_file_water"
        ]  # fixme: improve handing down args
        task_control = TaskControl(bpod=self.bpod, task_settings=task_settings)
        self.bpod.softcode_handler_function = task_control.softcode_handler

        trial_index = 0
        max_trials = task_settings["n_max_trials"]
        while self.continue_task and trial_index < max_trials:
            logging.info(f"Trial: {trial_index}")

            if trial_index == 0 and not task_settings["testing"]:
                sma = make_ttl_identifier_sequences(
                    bpod=self.bpod,
                    sequence=task_settings["ttl_identifier_sequence"],
                    output_chanel_pulse=eval(
                        f"Bpod.OutputChannels.BNC{task_settings['HARDWARE_BNC_TRIAL_START']}"
                    ),
                )
            else:
                sma = task_control.draw_next_trial()

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                self.input_kwargs["objects"]["kill_queue"].put(True)
                break

            trial_data = self.bpod.session.current_trial.export()
            task_control.update(trial_index=trial_index, trial_data=trial_data)
            if task_settings["show_live_plot"] and trial_index > 0:
                self.input_kwargs["objects"]["data_queue"].put(
                    {
                        "trial_index": task_control.trial_index,
                        "moving_average": task_control.moving_average.avg,
                        "block_probability_left": task_control.probability_left,
                        "block_probability_right": task_control.probability_right,
                        "choice": task_control.last_choice,
                        "rewarded": task_control.last_rewarded,
                        "was_stop": task_control.last_stop,
                        "punished": task_control.last_punish,
                    }
                )

            task_control.save()
            trial_index += 1

        self.input_kwargs["objects"]["kill_queue"].put(True)
        logging.debug("Exiting Task.")


def run_task(**args_dict):
    """Task: PS."""
    # Make objects
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

    # Do not auto start, so that camera can start first
    args_dict.update({"auto_start": False})

    # Enter behaviour context
    with TaskProcess(**args_dict) as tp:
        # Video
        conductor_args = {
            "config_file": args_dict["config_file_camera"],
            "acquisition_group": args_dict["is_child_session_to"]
            if args_dict["is_child_session_to"] is not None
            else tp.session_paths["session_basename"].split("__")[0],
            "acquisition_name": tp.session_paths["session_basename"],
        }
        c = Conductor(**conductor_args)
        c.start_acquisition()

        # FIXME: video stream config should come from RCC config -> add transpose etc. to 'stream' section in RCC
        video_stream_config = {
            "stream1": {
                "ip_address": "192.168.100.21",
                "port": 9999,
                "transpose": True,
            }
            # "stream2": "http://192.168.100.22:9999",
            # "stream3": "http://192.168.100.23:9999",
        }

        # Online plotting
        plotting_process = OnlinePlottingForPS(
            session_name=tp.session_paths["session_basename"],
            is_simulation=False,
            data_queue=dq,
            kill_queue=kq,
            video_stream_config=video_stream_config,
        )
        plotting_process.start()

        # Delay for video to start
        time.sleep(5)

        # Start task
        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        # Stop online plotting
        kq.put(True)

        # Stop video
        c.stop_acquisition()
        c.cleanup()

        time.sleep(1)


if __name__ == "__main__":
    run_task()
    print("main")
