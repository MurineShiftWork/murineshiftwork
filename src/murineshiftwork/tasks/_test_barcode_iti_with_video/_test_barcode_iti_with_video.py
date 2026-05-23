"""
Test protocol: TTL barcode at start of ITI, single BNC channel, with rpi_camera_ensemble.

Trial structure (every trial):
    barcode_start -> [barcode segments] -> iti_post_barcode -> ttl_on -> ttl_off -> wait -> exit

Identical trial logic to _test_barcode_iti. Video is handled in run_task().

Hardware:
    HARDWARE_BNC_CHANNEL: 1  ->  ephys digital input + RCE TTL-in + barcode + trial onset
    BNC2 reserved for PulsePal, not used here.

After the session:
    python tests/test_rce_barcode_alignment.py --session /data/subject/session_dir
    python tests/test_ephys_barcode_alignment.py --session ... --oe_dir ... --line 1
"""

import logging
import time
from pathlib import Path

from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine
from rpi_camera_ensemble.conductor.conductor import Conductor
from rpi_camera_ensemble.config.acquisition import EnsembleAcquisitionConfig
from rpi_camera_ensemble.config.conductor import ConductorConfig
from ttl_barcoder.core.barcode_ttl import BarcodeTTL

from murineshiftwork.hardware.bpod.ttl import add_trial_onset_ttl
from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    barcode_config_from_settings,
    inject_barcode_states,
    prepare_barcode,
)
from murineshiftwork.logic.io import save_trial_data
from murineshiftwork.logic.misc import draw_jittered_trial_time
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner

_DEFAULTS = {
    "n_max_trials": 20,
    "ttl_pulse_duration": 0.010,
    "inter_trial_interval": [2, 5, 0.5],  # [min_s, max_s, jitter_s]
    "wait_duration": 1.0,  # simulated task trial duration
    "HARDWARE_BNC_CHANNEL": 1,  # BNC1: barcode + trial onset
    "barcode_bits": 37,
    "barcode_bit_duration_ms": 35.0,
    "barcode_init_duration_ms": 10.0,
}


class Task(TaskRunner):
    """Identical trial logic to _test_barcode_iti — video is handled in run_task()."""

    def run(self):
        s = {**_DEFAULTS, **self.input_kwargs.get("settings.task.patched", {})}

        barcode_cfg = barcode_config_from_settings(s)
        barcoder = BarcodeTTL(barcode_cfg)
        barcode_duration_s = barcode_cfg.total_duration_ms / 1000.0

        bnc = eval(f"Bpod.OutputChannels.BNC{s['HARDWARE_BNC_CHANNEL']}")

        save_path = Path(self.bpod.workspace_path) / self.bpod.session_name
        trial_data_list = []

        logging.info(
            f"Barcode config: {barcode_cfg} | "
            f"duration {barcode_duration_s:.3f}s | "
            f"BNC{s['HARDWARE_BNC_CHANNEL']} (barcode + trial onset)"
        )

        trial_index = 0
        max_trials = s["n_max_trials"]

        while self.continue_task and trial_index < max_trials:
            logging.info(f"Trial {trial_index}")

            iti_spec = s["inter_trial_interval"]
            iti_this_trial = (
                draw_jittered_trial_time(*iti_spec)
                if isinstance(iti_spec, list | tuple) and len(iti_spec) == 3
                else float(iti_spec)
            )
            iti_post_barcode = max(0.05, iti_this_trial - barcode_duration_s)

            barcode_value, barcode_wall_time, timing_sequence = prepare_barcode(
                barcoder
            )

            logging.info(
                f"  barcode={barcode_value}  iti={iti_this_trial:.2f}s  "
                f"post={iti_post_barcode:.2f}s  barcode={barcode_duration_s:.2f}s"
            )

            sma = StateMachine(bpod=self.bpod)

            # 1. Barcode at start of ITI on BNC1
            sma = inject_barcode_states(
                sma=sma,
                timing_sequence=timing_sequence,
                bnc_channel=bnc,
                first_state_name=BARCODE_FIRST_STATE_NAME,
                last_state_name="iti_post_barcode",
            )

            # 2. Remaining ITI after barcode
            sma.add_state(
                state_name="iti_post_barcode",
                state_timer=iti_post_barcode,
                state_change_conditions={Bpod.Events.Tup: "ttl_on"},
                output_actions=[],
            )

            # 3. Trial-onset pulse on same BNC1 channel
            sma = add_trial_onset_ttl(
                sma=sma,
                state_name_tuple=("ttl_on", "ttl_off"),
                ttl_pulse_duration=s["ttl_pulse_duration"],
                bnc_channel=bnc,
                next_state="wait",
            )

            # 4. Simulated task trial (placeholder for real task states)
            sma.add_state(
                state_name="wait",
                state_timer=s["wait_duration"],
                state_change_conditions={Bpod.Events.Tup: "exit"},
                output_actions=[],
            )

            self.bpod.send_state_machine(sma)
            if not self.bpod.run_state_machine(sma):
                logging.warning(f"No data on trial {trial_index}. Stopping.")
                break

            trial_data = self.bpod.session.current_trial.export()
            trial_data["info"] = {
                "trial_type": "task",
                "trial_index": trial_index,
                "barcode_value": barcode_value,
                "barcode_wall_time": barcode_wall_time,
                "iti_total_s": round(iti_this_trial, 4),
                "iti_post_barcode_s": round(iti_post_barcode, 4),
                "barcode_duration_s": round(barcode_duration_s, 4),
                "barcode_config": barcode_cfg.model_dump(),
            }
            trial_data_list.append(trial_data)

            save_trial_data(trial_data_list, str(save_path) + ".df.jsonl")

            trial_index += 1

        logging.info(f"Task complete. {trial_index} trials run.")


def run_task(**args_dict):
    """Run barcode ITI test with rpi_camera_ensemble video recording."""
    args_dict.update({"auto_start": False})

    ensemble_cfg_file = args_dict["config_file_camera"]
    assert Path(ensemble_cfg_file).exists(), (
        f"Camera config not found: {ensemble_cfg_file}"
    )
    ensemble_cfg = EnsembleAcquisitionConfig.from_yaml(path=ensemble_cfg_file)
    conductor_cfg = ConductorConfig(data_dir=args_dict.get("out_path"))
    conductor = Conductor(config=conductor_cfg, ensemble_config=ensemble_cfg)
    conductor.start()
    conductor.setup_agents()

    with TaskProcess(**args_dict) as tp:
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

        # Give rpi cameras time to start recording before first barcode
        time.sleep(3)

        tp.run_task()
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()

        conductor.stop_acquisition()
        conductor.stop()

        time.sleep(1)


if __name__ == "__main__":
    print("main")
