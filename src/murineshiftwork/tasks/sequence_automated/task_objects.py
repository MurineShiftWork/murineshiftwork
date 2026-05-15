import json
import logging
import time
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from murineshiftwork.logic.barcode import BARCODE_FIRST_STATE_NAME
from murineshiftwork.logic.calibration import CalibrationDataWater
from murineshiftwork.logic.sounds import StereoSound
from murineshiftwork.io.trial_data import save_trial_data

log = logging.getLogger(__name__)

# All physical ports on the Bpod (1-indexed)
_ALL_PORTS = list(range(1, 9))

# Per-subject level state is stored here
LEVEL_STORE_DIR = Path("~/.murineshiftwork/sequence_automated").expanduser()


class TaskControl:
    trial_data = []
    trial_index = 0
    last_outcome = None  # "correct" | "incorrect"
    current_level = 1

    _valve_time_cache: dict

    def __init__(self, bpod=None, task_settings=None):
        if bpod is None:
            raise ValueError("bpod required")
        self.bpod = bpod
        self.task_settings = task_settings
        self.trial_data = []
        self._valve_time_cache = {}

        self.sequence = list(task_settings["sequence"])
        self.n_pokes = len(self.sequence)
        self.bnc_channel = eval(f"Bpod.OutputChannels.BNC{task_settings['HARDWARE_BNC_TRIAL_START']}")
        subject = task_settings["subject"]

        # Training levels table
        levels_file = task_settings.get("training_levels_file") or str(
            Path(__file__).parent / "training_levels.csv"
        )
        self.levels_df = self._load_levels(levels_file)

        # Training level: either reset to start_level or resume from disk
        if task_settings.get("reset_level", False):
            self.current_level = task_settings.get("start_level", 1)
            log.info(f"{subject}: reset_level=True, starting at level {self.current_level}")
        else:
            self.current_level = self._load_level(subject)
            log.info(f"{subject}: resuming at level {self.current_level}")

        self._session_start_level = self.current_level

        # Rolling performance buffer; cleared on every level change
        buf_size = task_settings.get("buffer_trials", 10)
        self.perf_buffer = deque(maxlen=buf_size)
        # Level 1 requires a minimum trial count before progression is checked
        self.level_1_trial_count = 0

        # Sound: non-blocking chirp played on every correct poke
        self.sound = StereoSound(sound_device=StereoSound.default_sound_device)
        self.sound_reward_code = self.sound.register_new_sound(
            frequency=task_settings.get("reward_sound_frequency", 8000),
            duration=task_settings.get("reward_sound_duration", 0.3),
            amplitude=task_settings.get("reward_sound_amplitude", 0.05),
            play_blocking=False,
        )

        # Water calibration
        self.calibration_water = CalibrationDataWater(
            file_path=task_settings["calibration_file_water"]
        )

        # Save path: prefer session_paths if provided
        session_paths = task_settings.get("session_paths", {})
        if session_paths.get("session_file_path"):
            self.save_path = Path(session_paths["session_file_path"])
        else:
            self.save_path = Path(self.bpod.workspace_path) / self.bpod.session_name

        # Persist task settings alongside data
        settings_to_save = {k: v for k, v in task_settings.items() if isinstance(v, (str, int, float, bool, list, type(None)))}
        with open(str(self.save_path) + ".settings.task.json", "w") as f:
            json.dump(settings_to_save, f, indent=4, sort_keys=True)

        # Register subject in the per-protocol registry
        self._register_subject(subject)

        log.debug("TaskControl initialised.")

    # ------------------------------------------------------------------ #
    # Level persistence                                                    #
    # ------------------------------------------------------------------ #

    def _level_file(self, subject: str) -> Path:
        return LEVEL_STORE_DIR / f"{subject}_level.json"

    def _load_level(self, subject: str) -> int:
        f = self._level_file(subject)
        if f.exists():
            data = json.loads(f.read_text())
            level = int(data.get("level", self.task_settings.get("start_level", 1)))
            level = max(1, min(level, len(self.levels_df)))
            return level
        return int(self.task_settings.get("start_level", 1))

    def _save_level(self):
        subject = self.task_settings["subject"]
        LEVEL_STORE_DIR.mkdir(parents=True, exist_ok=True)
        self._level_file(subject).write_text(
            json.dumps(
                {"level": self.current_level, "updated": time.strftime("%Y-%m-%dT%H:%M:%S")},
                indent=2,
            )
        )

    def _register_subject(self, subject: str):
        """Keep a JSON registry of all subjects and their last session."""
        LEVEL_STORE_DIR.mkdir(parents=True, exist_ok=True)
        registry_file = LEVEL_STORE_DIR / "subjects.json"
        registry = json.loads(registry_file.read_text()) if registry_file.exists() else {}
        registry[subject] = {
            "last_session": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "level": self.current_level,
        }
        registry_file.write_text(json.dumps(registry, indent=2))

    # ------------------------------------------------------------------ #
    # Training levels                                                      #
    # ------------------------------------------------------------------ #

    def _load_levels(self, filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, header=None)
        df.columns = [
            "reward1", "reward2", "reward3", "reward4", "final_reward",
            "led1", "led2", "led3", "led4", "led5",
            "response_window_ms",
        ]
        return df

    def _get_level_params(self) -> dict:
        row = self.levels_df.iloc[self.current_level - 1]
        # CSV response windows are in ms and designed for head-fixed lick sequences.
        # Apply a configurable minimum so freely moving port-poke trials are achievable.
        raw_window_s = float(row["response_window_ms"]) / 1000.0
        min_window = float(self.task_settings.get("min_response_window_s", 2.0))
        response_window_s = max(raw_window_s, min_window)
        return {
            "rewards": [
                float(row["reward1"]), float(row["reward2"]), float(row["reward3"]),
                float(row["reward4"]), float(row["final_reward"]),
            ],
            "leds": [
                float(row["led1"]), float(row["led2"]), float(row["led3"]),
                float(row["led4"]), float(row["led5"]),
            ],
            "response_window_s": response_window_s,
        }

    # ------------------------------------------------------------------ #
    # Hardware helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_valve_time(self, port: int, amount_ul: float) -> float:
        """Return valve opening time (seconds) for a given port and volume.
        Returns 0.0 for zero-reward pokes so no valve fires."""
        if amount_ul <= 0.0:
            return 0.0
        key = (port, amount_ul)
        if key not in self._valve_time_cache:
            result = self.calibration_water.water_volume_to_valve_time(
                valves=[port], target_volume=amount_ul
            )
            self._valve_time_cache[key] = float(result[port])
        return self._valve_time_cache[key]

    @staticmethod
    def _scale_led(matlab_val: float) -> int:
        """Scale MATLAB LED intensity (0-90) to Bpod PWM range (0-255)."""
        return int(round(matlab_val / 90.0 * 255))

    # ------------------------------------------------------------------ #
    # State machine                                                        #
    # ------------------------------------------------------------------ #

    def softcode_handler(self, softcode=None):
        self.sound.execute_sound_handler(sound_code=softcode)

    def draw_next_trial(self) -> StateMachine:
        params = self._get_level_params()
        rewards = params["rewards"]
        leds = params["leds"]
        response_window = params["response_window_s"]

        sma = StateMachine(bpod=self.bpod)

        # One wait + reward state pair per poke in the sequence.
        # Long TTL pulse: BNC goes HIGH entering wait_poke_0 (trial start),
        # stays HIGH through all intermediate states, goes LOW in exit_seq (ITI start).
        # Rising edge = trial start, falling edge = sequence complete or punish done.
        for i, (port, reward_ul, led_val) in enumerate(
            zip(self.sequence, rewards, leds)
        ):
            led_pwm = self._scale_led(led_val)
            pwm_ch = eval(f"Bpod.OutputChannels.PWM{port}")
            valve_time = self._get_valve_time(port, reward_ul)
            next_state_after_reward = (
                f"wait_poke_{i + 1}" if i < self.n_pokes - 1 else "exit_seq"
            )

            # Wrong poke or timeout → punish; correct poke → reward
            wait_conditions = {Bpod.Events.Tup: "punish"}
            for p in _ALL_PORTS:
                event = eval(f"Bpod.Events.Port{p}In")
                wait_conditions[event] = f"reward_poke_{i}" if p == port else "punish"

            # BNC HIGH on first state entry (trial start marker)
            bnc_actions = [(self.bnc_channel, 1)] if i == 0 else []
            sma.add_state(
                state_name=f"wait_poke_{i}",
                state_timer=response_window,
                state_change_conditions=wait_conditions,
                output_actions=bnc_actions + ([(pwm_ch, led_pwm)] if led_pwm > 0 else []),
            )

            # Open valve (if reward > 0) and play chirp
            reward_actions = []
            if valve_time > 0:
                reward_actions.append((Bpod.OutputChannels.Valve, port))
            if self.task_settings.get("reward_sound", True):
                reward_actions.append(("SoftCode", self.sound_reward_code))

            sma.add_state(
                state_name=f"reward_poke_{i}",
                # State must be at least as long as valve time; min 1 ms so state is valid
                state_timer=max(valve_time, 0.001),
                state_change_conditions={Bpod.Events.Tup: next_state_after_reward},
                output_actions=reward_actions,
            )

        sma.add_state(
            state_name="punish",
            state_timer=self.task_settings.get("punish_duration", 0.5),
            state_change_conditions={Bpod.Events.Tup: "exit_seq"},
            output_actions=[],
        )

        sma.add_state(
            state_name="exit_seq",
            state_timer=self.task_settings.get("iti_duration", 0.4),
            state_change_conditions={Bpod.Events.Tup: "exit"},
            output_actions=[(self.bnc_channel, 0)],  # BNC LOW = ITI start
        )

        return sma

    # ------------------------------------------------------------------ #
    # Trial outcome + level update                                         #
    # ------------------------------------------------------------------ #

    def update(self, trial_index: int, trial_data: dict, barcode_value=None, barcode_wall_time=None):
        self.trial_index = trial_index

        first_state = str(list(trial_data["States timestamps"].keys())[0])
        if first_state.lower() == BARCODE_FIRST_STATE_NAME.lower():
            trial_data["info"] = {
                "trial_type": "barcode",
                "trial_index": trial_index,
                "barcode_value": barcode_value,
                "barcode_wall_time": barcode_wall_time,
            }
            self.trial_data.append(trial_data)
            return

        # Did the mouse complete the full sequence?
        st = trial_data["States timestamps"]
        last_reward_key = f"reward_poke_{self.n_pokes - 1}"
        is_correct = last_reward_key in st and not (
            np.isnan(np.array(st[last_reward_key][0])).all()
        )
        self.last_outcome = "correct" if is_correct else "incorrect"

        # Track buffer and level-1 trial count
        self.perf_buffer.append(1 if is_correct else 0)
        if self.current_level == 1:
            self.level_1_trial_count += 1

        # Snapshot level and params for this trial BEFORE any level change
        trial_level = self.current_level
        params = self._get_level_params()
        perf = float(np.mean(self.perf_buffer)) if self.perf_buffer else 0.0

        self._update_level()

        trial_data["info"] = {
            "trial_type": "task",
            "trial_index": trial_index,
            "level": trial_level,
            "outcome": self.last_outcome,
            "sequence": self.sequence,
            "reward_amounts": params["rewards"],
            "led_intensities": params["leds"],
            "perf_buffer_mean": perf,
            "perf_buffer_n": len(self.perf_buffer),
        }
        trial_data["analysis"] = {}
        self.trial_data.append(trial_data)

        _t = trial_data.get("Trial start timestamp", 0)
        print(
            f"[T={round(_t / 60, 1):>5} min] "
            f"Trial {trial_index:>4} | "
            f"Lvl {trial_level:>2}{'→'+str(self.current_level) if self.current_level != trial_level else '  '} | "
            f"{'CORRECT  ' if is_correct else 'incorrect'} | "
            f"Perf {perf:.2f} ({len(self.perf_buffer)}/{self.perf_buffer.maxlen})"
        )

    def _update_level(self):
        buf = self.perf_buffer
        n_levels = len(self.levels_df)

        # Level 1: need minimum trial count before progression check
        if self.current_level == 1:
            if self.level_1_trial_count < self.task_settings.get("level_1_min_trials", 50):
                return
            if len(buf) >= buf.maxlen and float(np.mean(buf)) >= 0.9:
                self._advance_level()
            return

        if len(buf) < buf.maxlen:
            return

        perf = float(np.mean(buf))
        prog_thresh = (
            self.task_settings.get("progression_threshold", 0.9)
            if self.current_level <= 13
            else self.task_settings.get("progression_threshold_advanced", 0.8)
        )
        reg_thresh = self.task_settings.get("regression_threshold", 0.2)

        if perf >= prog_thresh and self.current_level < n_levels:
            self._advance_level()
        elif perf < reg_thresh:
            prevent = self.task_settings.get("prevent_regression_below_start", True)
            floor = self._session_start_level if prevent else 1
            if self.current_level > floor:
                self._regress_level()

    def _advance_level(self):
        old = self.current_level
        self.current_level = min(self.current_level + 1, len(self.levels_df))
        self.perf_buffer.clear()
        self.level_1_trial_count = 0
        self._save_level()
        self._register_subject(self.task_settings["subject"])
        log.info(f"Level advanced: {old} → {self.current_level}")

    def _regress_level(self):
        old = self.current_level
        self.current_level = max(self.current_level - 1, 1)
        self.perf_buffer.clear()
        # Reset level-1 counter if we regressed back to level 1
        if self.current_level == 1:
            self.level_1_trial_count = 0
        self._save_level()
        self._register_subject(self.task_settings["subject"])
        log.info(f"Level regressed: {old} → {self.current_level}")

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def save(self):
        save_trial_data(self.trial_data, str(self.save_path) + ".df.jsonl")

    def __del__(self):
        self.save()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()
