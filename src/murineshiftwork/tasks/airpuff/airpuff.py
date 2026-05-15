import logging
import time
from pathlib import Path

import numpy as np
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
# from rpi_camera_colony.control.conductor import Conductor
from rpi_camera_ensemble.conductor.conductor import Conductor
from rpi_camera_ensemble.config.acquisition import (
    EnsembleAcquisitionConfig,
)
from rpi_camera_ensemble.config.conductor import ConductorConfig
from ttl_barcoder.core.barcode_ttl import BarcodeTTL

from murineshiftwork.io.trial_data import save_trial_data
from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    barcode_config_from_settings,
    inject_barcode_states,
    prepare_barcode,
)
from murineshiftwork.logic.misc import draw_jittered_trial_time
from murineshiftwork.logic.specific_state_machines import add_trial_onset_ttl
from murineshiftwork.logic.task_process import TaskProcess
from murineshiftwork.logic.task_process import TaskRunner


class AirPuff(object):
    input_kwargs = {}
    out_path = ""

    trial_data = []

    def __init__(self, out_path=None, **kwargs):
        self.out_path = out_path
        self.input_kwargs = kwargs

    def update(
        self,
        trial_index=None,
        air_puff_duration=None,
        iti_this_trial=None,
        trial_data=None,
        barcode_value=None,
        barcode_wall_time=None,
    ):
        first_state_name = str(
            list(trial_data["States timestamps"].keys())[0]
        ).lower()
        trial_type = (
            "barcode"
            if first_state_name.startswith(BARCODE_FIRST_STATE_NAME)
            else "task"
        )
        trial_data["info"] = {
            "trial_type": trial_type,
            "trial_index": trial_index,
            "air_puff_duration": air_puff_duration,
            "iti_this_trial": iti_this_trial,
            "barcode_value": barcode_value,
            "barcode_wall_time": barcode_wall_time,
        }
        return self.trial_data.append(trial_data)

    def save(self):
        save_trial_data(self.trial_data, str(self.out_path) + ".msw.jsonl")
        logging.debug(f"Saved session data to {str(self.out_path)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def __del__(self):
        self.save()


class Task(TaskRunner):
    _bnc_channel_trial_onset = Bpod.OutputChannels.BNC1
    _bnc_channel_stimulation = Bpod.OutputChannels.BNC2

    def run(self) -> None:
        task_settings = self.input_kwargs["settings.task.patched"]

        air_puff_durations = task_settings.get("air_puff_durations")
        n_repeats_per_duration = task_settings.get("n_repeats_per_duration")
        inter_trial_interval = task_settings.get("inter_trial_interval")
        HARDWARE_VALVE_FOR_AIR = task_settings.get("HARDWARE_VALVE_FOR_AIR")

        if (
            not air_puff_durations
            or not n_repeats_per_duration
            or not inter_trial_interval
        ):
            raise ValueError(
                [air_puff_durations, n_repeats_per_duration, inter_trial_interval]
            )

        barcode_cfg = barcode_config_from_settings(task_settings)
        barcoder = BarcodeTTL(barcode_cfg)
        bnc_channel = self._bnc_channel_trial_onset
        barcode_duration_s = barcode_cfg.total_duration_ms / 1000.0

        # Prepare
        _trial_types = np.asarray(
            [[dur] * n_repeats_per_duration for dur in air_puff_durations]
        )
        trial_types = np.random.permutation(_trial_types.flatten())

        air_puff_protocol = AirPuff(
            out_path=self.input_kwargs["session_paths"]["session_file_path"]
        )

        # Run
        trial_index = 0
        while self.continue_task and trial_index <= len(trial_types):
            logging.info(f"Executing trial {trial_index}")

            barcode_value = None
            barcode_wall_time = None

            if trial_index == 0:
                air_puff_duration = None
                iti_this_trial = None
                barcode_value, barcode_wall_time, timing_seq = prepare_barcode(barcoder)
                sma = StateMachine(bpod=self.bpod)
                sma = inject_barcode_states(sma, timing_seq, bnc_channel, last_state_name="exit")

            else:
                air_puff_duration = trial_types[trial_index - 1]
                iti_this_trial = draw_jittered_trial_time(*inter_trial_interval)
                barcode_value, barcode_wall_time, timing_seq = prepare_barcode(barcoder)
                iti_post_barcode = max(0.05, iti_this_trial - barcode_duration_s)

                sma = StateMachine(bpod=self.bpod)
                # Trial onset
                sma = add_trial_onset_ttl(
                    sma=sma,
                    ttl_pulse_duration=0.001,
                    bnc_channel=bnc_channel,
                    next_state="release_puff",
                )
                # Puff
                sma.add_state(
                    state_name="release_puff",
                    state_timer=air_puff_duration,
                    state_change_conditions={Bpod.Events.Tup: BARCODE_FIRST_STATE_NAME},
                    output_actions=[(Bpod.OutputChannels.Valve, HARDWARE_VALVE_FOR_AIR)],
                )
                # ITI barcode + post-barcode wait
                sma = inject_barcode_states(sma, timing_seq, bnc_channel, last_state_name="iti_post_barcode")
                sma.add_state(
                    state_name="iti_post_barcode",
                    state_timer=iti_post_barcode,
                    state_change_conditions={Bpod.Events.Tup: "exit"},
                    output_actions=[(bnc_channel, 0)],  # explicit LOW: BNC hold bug fix
                )

            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning(
                    f"No data returned on trial #{trial_index}. Terminating protocol."
                )
                break

            trial_data = self.bpod.session.current_trial.export()
            air_puff_protocol.update(
                trial_index=trial_index,
                air_puff_duration=air_puff_duration,
                iti_this_trial=iti_this_trial,
                trial_data=trial_data,
                barcode_value=barcode_value,
                barcode_wall_time=barcode_wall_time,
            )
            air_puff_protocol.save()
            trial_index += 1

        try:
            bv_end, bwt_end, timing_seq_end = prepare_barcode(barcoder)
            sma_end = StateMachine(bpod=self.bpod)
            sma_end = inject_barcode_states(sma_end, timing_seq_end, bnc_channel, last_state_name="exit")
            self.bpod.send_state_machine(sma_end)
            self.bpod.run_state_machine(sma_end)
            trial_data_end = self.bpod.session.current_trial.export()
            air_puff_protocol.update(
                trial_index=trial_index,
                trial_data=trial_data_end,
                barcode_value=bv_end,
                barcode_wall_time=bwt_end,
            )
            air_puff_protocol.save()
            logging.info("Session-end barcode sent.")
        except Exception:
            logging.warning("Session-end barcode failed.", exc_info=True)

        logging.debug("Exiting Task.")


def run_task(**args_dict):
    # Do not auto start, so that camera can start first
    args_dict.update({"auto_start": False})

    # Video
    ensemble_cfg_file = args_dict.get("config_file_camera", "")
    if not ensemble_cfg_file or not Path(ensemble_cfg_file).exists():
        raise FileNotFoundError(
            f"Camera ensemble config not found: {ensemble_cfg_file!r}. "
            "Set via SetupConfig cameras.config or --config-file-camera."
        )
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

        # Delay for video to start
        time.sleep(3)

        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        # Stop video
        conductor.stop_acquisition()
        conductor.stop()

        time.sleep(1)


if __name__ == "__main__":
    print("main")
