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
from pathlib import Path

from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine
from rpi_camera_ensemble.conductor.conductor import Conductor
from rpi_camera_ensemble.config.acquisition import (
    EnsembleAcquisitionConfig,
)
from rpi_camera_ensemble.config.conductor import ConductorConfig
from ttl_barcoder.core.barcode_ttl import BarcodeTTL

from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    barcode_config_from_settings,
    inject_barcode_states,
    prepare_barcode,
)
from murineshiftwork.logic.task_process import TaskProcess
from murineshiftwork.logic.task_process import TaskRunner
from murineshiftwork.tasks.probabilistic_switching_fixedsubjects.online_plotting import (
    OnlinePlottingForPS,
)
from murineshiftwork.tasks.probabilistic_switching_fixedsubjects.task_objects import (
    TaskControl,
)


class Task(TaskRunner):
    def run(self):
        task_settings = self.input_kwargs["settings.task.patched"]

        barcode_cfg = barcode_config_from_settings(task_settings)
        barcoder = BarcodeTTL(barcode_cfg)
        bnc_channel = eval(f"Bpod.OutputChannels.BNC{task_settings['HARDWARE_BNC_TRIAL_START']}")

        task_control = TaskControl(bpod=self.bpod, task_settings=task_settings, barcoder=barcoder)
        self.bpod.softcode_handler_function = task_control.softcode_handler

        trial_index = 0
        max_trials = task_settings["n_max_trials"]
        while self.continue_task and trial_index < max_trials:
            logging.info(f"Trial: {trial_index}")

            barcode_value = None
            barcode_wall_time = None

            if trial_index == 0 and not task_settings["testing"]:
                barcode_value, barcode_wall_time, timing_seq = prepare_barcode(barcoder)
                sma = StateMachine(bpod=self.bpod)
                sma = inject_barcode_states(sma, timing_seq, bnc_channel, last_state_name="exit")
            else:
                sma = task_control.draw_next_trial()

            self.bpod.send_state_machine(sma)

            try:
                has_run = self.bpod.run_state_machine(sma)
            except TypeError:
                has_run = False

            if not has_run:
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                trial_index += 1

            trial_data = self.bpod.session.current_trial.export()
            task_control.update(
                trial_index=trial_index,
                trial_data=trial_data,
                barcode_value=barcode_value,
                barcode_wall_time=barcode_wall_time,
            )
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
                        "forced_choice": task_control.last_forced_choice,
                    }
                )

            task_control.save()
            trial_index += 1

        if not task_settings["testing"]:
            try:
                bv_end, bwt_end, timing_seq_end = prepare_barcode(barcoder)
                sma_end = StateMachine(bpod=self.bpod)
                sma_end = inject_barcode_states(sma_end, timing_seq_end, bnc_channel, last_state_name="exit")
                self.bpod.send_state_machine(sma_end)
                self.bpod.run_state_machine(sma_end)
                trial_data_end = self.bpod.session.current_trial.export()
                task_control.update(
                    trial_index=trial_index,
                    trial_data=trial_data_end,
                    barcode_value=bv_end,
                    barcode_wall_time=bwt_end,
                )
                task_control.save()
                logging.info("Session-end barcode sent.")
            except Exception:
                logging.warning("Session-end barcode failed to send.", exc_info=True)

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

    setup_name = args_dict.get("metadata", {}).get("setup", "n/a")

    # Video
    ensemble_cfg_file = args_dict["config_file_camera"]
    print("DBG:", ensemble_cfg_file)
    assert Path(ensemble_cfg_file).exists()
    ensemble_cfg = EnsembleAcquisitionConfig.from_yaml(path=ensemble_cfg_file)
    conductor_cfg = ConductorConfig(data_dir=args_dict.get("out_path", None))
    conductor = Conductor(config=conductor_cfg, ensemble_config=ensemble_cfg)
    conductor.start()
    conductor.setup_agents()

    # Enter behaviour context
    with TaskProcess(**args_dict) as tp:
        # Paths for video
        _session = tp.session_paths["session_basename"]
        _subject = tp.session_paths["subject"]

        conductor.initialize_acquisition(
            acquisition_path=(
                f"{_subject}/{args_dict['is_child_session_to']}/{_session}"
                if args_dict["is_child_session_to"] is not None
                else f"{_subject}/{_session}"
            ),
            acquisition_name=_session,
        )
        conductor.start_preview()
        conductor.start_recording()
        # assert 1 == 0
        # conductor_args = {
        #     "config_file": args_dict["config_file_camera"],
        #     "acquisition_group": args_dict["is_child_session_to"]
        #     if args_dict["is_child_session_to"] is not None
        #     else tp.session_paths["session_basename"].split("__")[0],
        #     "acquisition_name": tp.session_paths["session_basename"],
        # }
        # c = Conductor(**conductor_args)
        # c.start_acquisition()
        # FIX-ME: video stream config should come from RCC config -> add transpose etc. to 'stream' section in RCC
        # video_stream_config = args_dict["settings.camera"].get(
        #     "controllers", {}
        # )

        # Online plotting
        plotting_process = OnlinePlottingForPS(
            window_title=f"[{setup_name}]  {tp.session_paths['session_basename']}",
            is_simulation=False,
            data_queue=dq,
            kill_queue=kq,
            # video_stream_config=video_stream_config,
        )
        plotting_process.start()

        # if piezo, then expect params to start intan lick detection
        # piezo_ip = "192.168.100.19"
        # use_piezo_lick_detection = tp.input_kwargs["settings.task.patched"].get(
        #     "use_piezo_lick_detection", False
        # )
        # use_piezo_lick_detection = True
        #
        # if use_piezo_lick_detection:
        #     logging.info(f"Starting piezo lick detection on {piezo_ip}")
        #     run_record(
        #         ip=piezo_ip,
        #         local_path="/mnt/fastdata/data",
        #         remote_path="/home/lbr/data",
        #         session_extension="ephys_intan_lick",
        #         subject=args_dict["subject"],
        #         is_child_session_to=args_dict["is_child_session_to"],
        #         acquisition_extension="ephys_multi_behavior",
        #     )

        # Delay for video to start
        time.sleep(3)

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
        # c.stop_acquisition()
        # c.cleanup()
        conductor.stop_acquisition()
        conductor.stop()

        # # Stop piezo lick detection
        # if use_piezo_lick_detection:
        #     run_stop(ip=piezo_ip)

        time.sleep(1)


if __name__ == "__main__":
    run_task()
    print("main")
