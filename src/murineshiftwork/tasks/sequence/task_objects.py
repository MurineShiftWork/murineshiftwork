import json
import logging
import time
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod, StateMachine

from murineshiftwork.logic.barcode import BARCODE_FIRST_STATE_NAME
from murineshiftwork.logic.calibration import CalibrationDataWater
from murineshiftwork.logic.io import save_trial_data
from murineshiftwork.logic.sounds import StereoSound

log = logging.getLogger(__name__)

# All physical ports on the Bpod (1-indexed)
_ALL_PORTS = list(range(1, 9))

# Per-subject level state is stored here
LEVEL_STORE_DIR = Path("~/.murineshiftwork/sequence").expanduser()
_LEGACY_LEVEL_STORE_DIR = Path("~/.murineshiftwork/sequence_automated").expanduser()


class TaskControl:
    trial_data: list = []
    trial_index = 0
    last_outcome: str | None = None
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
        self.bnc_channel = getattr(
            Bpod.OutputChannels, f"BNC{task_settings['HARDWARE_BNC_TRIAL_START']}"
        )
        subject = task_settings["subject"]

        # Training levels table
        levels_file = task_settings.get("training_levels_file") or str(
            Path(__file__).parent / "training_levels.csv"
        )
        self.levels_df = self._load_levels(levels_file)

        # Training level: either reset to start_level or resume from disk
        if task_settings.get("reset_level", False):
            self.current_level = int(task_settings.get("start_level", 1))
            log.info(
                f"{subject}: reset_level=True, starting at level {self.current_level}"
            )
        else:
            self.current_level = self._load_level(subject)
            log.info(f"{subject}: starting at level {self.current_level}")

        self._session_start_level = self.current_level

        # Rolling performance buffer; cleared on every level change
        buf_size = task_settings.get("buffer_trials", 10)
        self.perf_buffer = deque(maxlen=buf_size)
        # Level 1 requires a minimum trial count before progression is checked
        self.level_1_trial_count = 0

        # Sound: non-blocking chirp played on every correct poke
        sound_device = (
            task_settings.get("reward_sound_device") or StereoSound.default_sound_device
        )
        self.sound = StereoSound(sound_device=sound_device)
        self.sound.setup_sound_device()
        self.sound_reward_code = self.sound.register_new_sound(
            frequency=task_settings.get("reward_sound_frequency", -1),
            duration=task_settings.get("reward_sound_duration", 0.2),
            amplitude=task_settings.get("reward_sound_amplitude", 0.15),
            play_blocking=False,
        )

        # Session-level reward tracking
        self._session_reward_count = 0
        self._session_water_ul = 0.0

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

        from murineshiftwork.logic.task_process import update_session_yaml

        settings_to_save = {
            k: v
            for k, v in task_settings.items()
            if isinstance(v, (str, int, float, bool, list, type(None)))
        }
        update_session_yaml(self.save_path, task_settings=settings_to_save)

        # Register subject in the per-protocol registry
        self._register_subject(subject)

        log.debug("TaskControl initialised.")

    # ------------------------------------------------------------------ #
    # Level persistence                                                    #
    # ------------------------------------------------------------------ #

    def _level_file(self, subject: str) -> Path:
        return LEVEL_STORE_DIR / f"{subject}_level.json"

    # ---------------------------------------------------------------------- #
    # Subject state source — swap these two methods for LabWatch API calls  #
    # when subjects need to roam between setups.                             #
    # Local contract: level file at LEVEL_STORE_DIR/{subject}_level.json    #
    # Remote contract (future): GET/POST to LabWatch /subjects/{name}/state #
    # ---------------------------------------------------------------------- #

    def _fetch_subject_state(self, subject: str) -> dict:
        """Load per-subject task state from the local store.

        TODO: replace with LabWatch API GET when moving to multi-setup tracking.
        """
        f = self._level_file(subject)
        if f.exists():
            return json.loads(f.read_text())
        # Migrate from legacy sequence_automated store on first access
        legacy = _LEGACY_LEVEL_STORE_DIR / f"{subject}_level.json"
        if legacy.exists():
            log.info(
                f"Migrating level state for {subject} from legacy sequence_automated store."
            )
            return json.loads(legacy.read_text())
        return {}

    def _push_subject_state(self, subject: str, state: dict):
        """Persist per-subject task state to the local store.

        TODO: replace with LabWatch API POST when moving to multi-setup tracking.
        """
        LEVEL_STORE_DIR.mkdir(parents=True, exist_ok=True)
        self._level_file(subject).write_text(json.dumps(state, indent=2))

    # ---------------------------------------------------------------------- #

    def _load_level(self, subject: str) -> int:
        # task_settings["start_level"] is the authoritative source — it is kept
        # current by save_session_end() writing the end-of-session level back to
        # the subject YAML as task_overrides.sequence.start_level.  The JSON store
        # (_fetch_subject_state) is therefore no longer consulted here; it still
        # receives writes from _save_level() as a crash-recovery fallback.
        level = int(self.task_settings.get("start_level", 1))
        return max(1, min(level, len(self.levels_df)))

    def _save_level(self):
        subject = self.task_settings["subject"]
        existing = self._fetch_subject_state(subject)
        existing.update(
            {
                "level": self.current_level,
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
        self._push_subject_state(subject, existing)

    def save_session_end(self):
        """Persist final session state regardless of whether the level changed.

        Call this once after the trial loop exits so the local (or remote) store
        always reflects the most recent session even when performance was flat.
        Also writes start_level back to the subject YAML in config_dir so the
        progression is git-tracked and portable across machines.
        """
        subject = self.task_settings["subject"]
        existing = self._fetch_subject_state(subject)
        existing.update(
            {
                "level": self.current_level,
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "session_start_level": self._session_start_level,
                "total_trials": self.trial_index,
            }
        )
        self._push_subject_state(subject, existing)
        self._register_subject(subject)
        log.info(
            f"Session end state saved for '{subject}': level {self.current_level}, "
            f"trials {self.trial_index}"
        )

        config_dir = self.task_settings.get("config_dir", "")
        if config_dir and subject and not subject.startswith("_test_"):
            try:
                from murineshiftwork.logic.config.io import save_subject_task_overrides

                save_subject_task_overrides(
                    config_dir, subject, "sequence", {"start_level": self.current_level}
                )
                log.debug(
                    f"Wrote start_level={self.current_level} to subject YAML for '{subject}'"
                )
            except Exception as exc:
                log.warning(f"Could not write level to subject YAML: {exc}")

    def _register_subject(self, subject: str):
        """Keep a JSON registry of all subjects and their last session."""
        LEVEL_STORE_DIR.mkdir(parents=True, exist_ok=True)
        registry_file = LEVEL_STORE_DIR / "subjects.json"
        registry = (
            json.loads(registry_file.read_text()) if registry_file.exists() else {}
        )
        registry[subject] = {
            "last_session": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "level": self.current_level,
        }
        registry_file.write_text(json.dumps(registry, indent=2))

    # ------------------------------------------------------------------ #
    # Training levels                                                      #
    # ------------------------------------------------------------------ #

    def _load_levels(self, filepath: str) -> pd.DataFrame:
        df = (
            pd.read_csv(filepath, index_col="level")
            if self._has_header(filepath)
            else self._load_levels_legacy(filepath)
        )
        return df

    @staticmethod
    def _has_header(filepath: str) -> bool:
        with open(filepath) as f:
            return not f.readline()[0].isdigit()

    @staticmethod
    def _load_levels_legacy(filepath: str) -> pd.DataFrame:
        df = pd.read_csv(filepath, header=None)
        df.columns = [
            "reward1",
            "reward2",
            "reward3",
            "reward4",
            "final_reward",
            "led1",
            "led2",
            "led3",
            "led4",
            "led5",
            "response_window_s",
        ]
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="level")
        return df

    def _get_level_params(self) -> dict:
        row = self.levels_df.loc[self.current_level]
        return {
            "rewards": [
                float(row["reward1"]),
                float(row["reward2"]),
                float(row["reward3"]),
                float(row["reward4"]),
                float(row["final_reward"]),
            ],
            "leds": [
                float(row["led1"]),
                float(row["led2"]),
                float(row["led3"]),
                float(row["led4"]),
                float(row["led5"]),
            ],
            "response_window_s": float(row["response_window_s"]),
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

    # ------------------------------------------------------------------ #
    # Scoring — MATLAB UpdateLevel.m algorithm                            #
    # ------------------------------------------------------------------ #

    def _score_sequence_matlab(self, trial_data: dict) -> bool:
        """Detect if the target sequence occurred in raw port events.

        Mirrors UpdateLevel.m: collect all PortIn timestamps, sort by time,
        remove consecutive duplicate ports, then use strfind (contiguous
        subsequence search) to detect the template.
        """
        events = trial_data.get("Events timestamps", {})
        poke_events: list[tuple[float, int]] = []
        for port in range(1, 9):
            for t in events.get(f"Port{port}In", []):
                poke_events.append((t, port))
        if not poke_events:
            return False
        poke_events.sort()
        deduped: list[int] = []
        for _, port in poke_events:
            if not deduped or deduped[-1] != port:
                deduped.append(port)
        template = list(self.sequence)
        n = len(template)
        for i in range(len(deduped) - n + 1):
            if deduped[i : i + n] == template:
                return True
        return False

    def _extract_poke_events(self, trial_data: dict) -> list:
        """Return all port-in events sorted by time with t=0 at first poke."""
        events = trial_data.get("Events timestamps", {})
        raw = []
        for port in range(1, 9):
            for t in events.get(f"Port{port}In", []):
                raw.append({"port": port, "host_ts": t})
        raw.sort(key=lambda x: x["host_ts"])
        if raw:
            t0 = raw[0]["host_ts"]
            for p in raw:
                p["time"] = round(p["host_ts"] - t0, 4)
                del p["host_ts"]
        return raw

    @staticmethod
    def _compute_transition_times(poke_events: list) -> list:
        """Inter-poke transition times from sorted poke event list."""
        transitions: list[dict] = []
        prev = None
        for p in poke_events:
            if prev is not None:
                transitions.append(
                    {
                        "from": prev["port"],
                        "to": p["port"],
                        "dt": round(p["time"] - prev["time"], 4),
                    }
                )
            prev = p
        return transitions

    def draw_next_trial(self) -> StateMachine:
        params = self._get_level_params()
        # Pad rewards/leds to sequence length so sequences longer than 5 pokes work
        rewards = params["rewards"]
        leds = params["leds"]
        while len(rewards) < self.n_pokes:
            rewards.append(rewards[-1])
        while len(leds) < self.n_pokes:
            leds.append(leds[-1])
        response_window = params["response_window_s"]

        # strict_sequence=True: any wrong poke immediately triggers punish (strict mode)
        # strict_sequence=False (default): wrong pokes ignored; only timeout or correct
        # poke causes a state transition — equivalent to the original MATLAB behaviour
        strict = self.task_settings.get("strict_sequence", False)

        sma = StateMachine(bpod=self.bpod)

        for i, (port, reward_ul, led_val) in enumerate(
            zip(self.sequence, rewards, leds)
        ):
            led_pwm = self._scale_led(led_val)
            pwm_ch = getattr(Bpod.OutputChannels, f"PWM{port}")
            valve_time = self._get_valve_time(port, reward_ul)
            next_state_after_reward = (
                f"wait_poke_{i + 1}" if i < self.n_pokes - 1 else "exit_seq"
            )

            if i == 0:
                # First poke: no timeout, no Tup condition — MATLAB WaitForInitialPoke
                # has Timer=0 with only the correct port event; Tup would fire immediately
                # at timer=0 and must not be present.
                wait_conditions = {
                    getattr(Bpod.Events, f"Port{port}In"): f"reward_poke_{i}",
                }
                if strict:
                    for p in _ALL_PORTS:
                        if p != port:
                            wait_conditions[getattr(Bpod.Events, f"Port{p}In")] = (
                                "punish"
                            )
                state_timer = 0
            elif strict:
                wait_conditions = {Bpod.Events.Tup: "punish"}
                for p in _ALL_PORTS:
                    event = getattr(Bpod.Events, f"Port{p}In")
                    wait_conditions[event] = (
                        f"reward_poke_{i}" if p == port else "punish"
                    )
                state_timer = response_window
            else:
                wait_conditions = {
                    Bpod.Events.Tup: "punish",
                    getattr(Bpod.Events, f"Port{port}In"): f"reward_poke_{i}",
                }
                state_timer = response_window

            # BNC HIGH on first state entry (trial start marker)
            bnc_actions = [(self.bnc_channel, 1)] if i == 0 else []
            sma.add_state(
                state_name=f"wait_poke_{i}",
                state_timer=state_timer,
                state_change_conditions=wait_conditions,
                output_actions=bnc_actions
                + ([(pwm_ch, led_pwm)] if led_pwm > 0 else []),
            )

            # Open valve (if reward > 0) and play chirp
            reward_actions = []
            if valve_time > 0:
                reward_actions.append((Bpod.OutputChannels.Valve, port))
            if self.task_settings.get("reward_sound", True):
                reward_actions.append(("SoftCode", self.sound_reward_code))

            sma.add_state(
                state_name=f"reward_poke_{i}",
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

    def update(
        self,
        trial_index: int,
        trial_data: dict,
        barcode_value=None,
        barcode_wall_time=None,
    ):
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

        # MATLAB UpdateLevel.m algorithm: detect sequence as contiguous
        # subsequence in sorted-deduped port events (not just final state visited)
        is_correct = self._score_sequence_matlab(trial_data)
        self.last_outcome = "correct" if is_correct else "incorrect"

        # Track buffer and level-1 trial count
        self.perf_buffer.append(1 if is_correct else 0)
        if self.current_level == 1:
            self.level_1_trial_count += 1

        # Snapshot level and params for this trial BEFORE any level change
        trial_level = self.current_level
        params = self._get_level_params()
        perf = float(np.mean(self.perf_buffer)) if self.perf_buffer else 0.0

        # Count rewards/water actually dispensed this trial
        st = trial_data["States timestamps"]
        rewards_this_trial = 0
        water_this_trial = 0.0
        for i in range(self.n_pokes):
            rkey = f"reward_poke_{i}"
            if rkey in st and not np.isnan(np.array(st[rkey][0])).all():
                if params["rewards"][i] > 0:
                    rewards_this_trial += 1
                    water_this_trial += params["rewards"][i]
        self._session_reward_count += rewards_this_trial
        self._session_water_ul += water_this_trial

        # Extract poke events, transitions, and sequence duration for plotting
        poke_events = self._extract_poke_events(trial_data)
        transition_times = self._compute_transition_times(poke_events)
        sequence_duration_s = (
            round(poke_events[-1]["time"] - poke_events[0]["time"], 3)
            if is_correct and len(poke_events) >= 2
            else None
        )

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
            "reward_count_trial": rewards_this_trial,
            "water_ul_trial": round(water_this_trial, 2),
            "water_ul_cumulative": round(self._session_water_ul, 2),
            "poke_events": poke_events,
            "transition_times": transition_times,
            "sequence_duration_s": sequence_duration_s,
        }
        trial_data["analysis"] = {}
        self.trial_data.append(trial_data)

        _t = trial_data.get("Trial start timestamp", 0)
        lvl_arrow = (
            f"→{self.current_level}" if self.current_level != trial_level else "  "
        )
        n_correct = int(sum(self.perf_buffer))
        n_buf = len(self.perf_buffer)
        print(
            f"[T={round(_t / 60, 1):>5} min] "
            f"Trial {trial_index:>4} | "
            f"Lvl {trial_level:>2}{lvl_arrow:<3} | "
            f"{'CORRECT  ' if is_correct else 'incorrect'} | "
            f"Perf {perf:.2f} ({n_correct}/{n_buf}) | "
            f"R:{rewards_this_trial} {water_this_trial:.1f}uL | "
            f"Total:{self._session_water_ul:.1f}uL"
        )

    def _update_level(self):
        # Mirrors MATLAB UpdateLevel.m exactly: single progression_threshold,
        # strictly-greater comparison (> not >=), buffer must be full.
        buf = self.perf_buffer
        n_levels = len(self.levels_df)
        prog_thresh = self.task_settings.get("progression_threshold", 0.9)
        reg_thresh = self.task_settings.get("regression_threshold", 0.2)

        # Level 1: need minimum trial count before progression check
        if self.current_level == 1:
            if self.level_1_trial_count < self.task_settings.get(
                "level_1_min_trials", 50
            ):
                return
            if len(buf) >= buf.maxlen and float(np.mean(buf)) > prog_thresh:
                self._advance_level()
            return

        if len(buf) < buf.maxlen:
            return

        perf = float(np.mean(buf))
        if perf > prog_thresh and self.current_level < n_levels:
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
        if hasattr(self, "save_path"):
            self.save()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()
