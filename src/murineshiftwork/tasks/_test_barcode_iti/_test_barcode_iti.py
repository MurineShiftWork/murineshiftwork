"""
Test protocol: TTL barcode at start of ITI, single BNC channel.

Trial structure (every trial):
    barcode_start -> [barcode segments] -> iti_post_barcode -> ttl_on -> ttl_off -> wait -> exit

Barcode fires first on BNC1, followed by remaining ITI, then a short trial-onset
pulse on the same BNC1 channel, then a simulated task trial (wait state).

Single channel (HARDWARE_BNC_CHANNEL=1) carries both barcode and trial-onset pulse.
The barcode decoder segments on >500ms gaps, so the isolated trial-onset pulse
(~10ms, after iti_post_barcode >= 50ms gap) is unambiguous.

BNC2 is reserved for PulsePal and not used here.

Hardware:
    HARDWARE_BNC_CHANNEL: 1  ->  ephys digital input + RCE TTL-in

Alignment (per trial):
    barcode_value encodes Unix timestamp -> self-identifying, no ordering needed.
    df["barcode_start"].apply(lambda x: x[0][0]) -> Bpod clock time of first edge.
    barcode_wall_time -> Unix time at barcode generation.
    Match by value to ephys/RCE decoded barcodes -> per-trial linear fit.
"""

import logging
import time
from pathlib import Path

from pybpodapi.protocol import Bpod
from pybpodapi.state_machine import StateMachine

from murineshiftwork.hardware.bpod.ttl import add_trial_onset_ttl
from murineshiftwork.logic.barcode import (
    BARCODE_FIRST_STATE_NAME,
    BarcodeTTL,
    barcode_config_from_settings,
    inject_barcode_states,
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

            barcode_value, barcode_wall_time, timing_sequence = barcoder.prepare()

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


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
