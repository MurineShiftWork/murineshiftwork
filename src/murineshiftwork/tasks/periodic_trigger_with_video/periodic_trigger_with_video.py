import logging
import time
from pathlib import Path

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine
from rpi_camera_colony.control.conductor import Conductor

from murineshiftwork.hardware.bpod.ttl import add_trial_onset_ttl
from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    BarcodeTTL,
    barcode_config_from_settings,
    inject_barcode_states,
)
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner
from murineshiftwork.readers.io import save_trial_data


class TaskData:
    save_path = None
    data: list = []

    def __init__(self, save_path=None):
        super().__init__()
        self.save_path = save_path
        self.data = []

    def append(
        self,
        trial_index=None,
        trial_data=None,
        barcode_value=None,
        barcode_wall_time=None,
        **info_dict_extension,
    ):
        first_state_name = str(list(trial_data["States timestamps"].keys())[0]).lower()
        if first_state_name == BARCODE_FIRST_STATE_NAME.lower():
            trial_type = "barcode"
        else:
            trial_type = "task"

        trial_data["info"] = {
            "trial_type": trial_type,
            "trial_index": trial_index,
            "barcode_value": barcode_value,
            "barcode_wall_time": barcode_wall_time,
            **info_dict_extension,
        }
        self.data.append(trial_data)

    def save(self, save_path=None):
        save_path = save_path or self.save_path
        logging.debug("Saving task control data..")
        dt = time.time()
        save_trial_data(self.data, str(save_path) + ".df.jsonl")
        logging.debug(f"Saved data in {np.round(time.time() - dt, 2)}s.")


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
            f"periodic_trigger_with_video: iti={trigger_iti}s max={max_runtime}s "
            f"barcode every {barcode_every_n} trials ({barcode_interval_s}s)"
        )

        save_path = Path(self.bpod.workspace_path) / self.bpod.session_name
        task_data = TaskData(save_path=save_path)

        trial_index = 0
        while self.continue_task and trial_index <= n_max_trials:
            logging.info(
                f"Trial {trial_index}/{n_max_trials} "
                f"[{np.round(trial_index * trigger_iti / 60, 1)} min / "
                f"{np.round(max_runtime / 60, 1)} min]"
            )

            barcode_value = None
            barcode_wall_time = None

            if trial_index == 0 or trial_index % barcode_every_n == 0:
                barcode_value, barcode_wall_time, timing_seq = barcoder.prepare()
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

            task_data.append(
                trial_index=trial_index,
                trial_data=self.bpod.session.current_trial.export(),
                barcode_value=barcode_value,
                barcode_wall_time=barcode_wall_time,
            )
            task_data.save()
            trial_index += 1

        try:
            bv_end, bwt_end, timing_seq_end = barcoder.prepare()
            sma_end = StateMachine(bpod=self.bpod)
            sma_end = inject_barcode_states(
                sma_end, timing_seq_end, bnc_channel, last_state_name="exit"
            )
            self.bpod.send_state_machine(sma_end)
            self.bpod.run_state_machine(sma_end)
            task_data.append(
                trial_index=trial_index,
                trial_data=self.bpod.session.current_trial.export(),
                barcode_value=bv_end,
                barcode_wall_time=bwt_end,
            )
            task_data.save()
            logging.info("Session-end barcode sent.")
        except Exception:
            logging.warning("Session-end barcode failed to send.", exc_info=True)


def run_task(**args_dict):
    args_dict.update({"auto_start": False})

    with TaskProcess(**args_dict) as tp:
        conductor_args = {
            "config_file": args_dict["config_file_camera"],
            "acquisition_group": args_dict["is_child_session_to"]
            if args_dict["is_child_session_to"] is not None
            else tp.session_paths["session_basename"].split("__")[0],
            "acquisition_name": tp.session_paths["session_basename"],
        }
        c = Conductor(**conductor_args)
        c.start_acquisition()

        time.sleep(5)

        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

    c.stop_acquisition()
    c.cleanup()

    time.sleep(1)


if __name__ == "__main__":
    print("main")
