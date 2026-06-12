import json
import logging
import time
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod, StateMachine

from murineshiftwork.logic.barcode import BARCODE_FIRST_STATE_NAME
from murineshiftwork.logic.io import save_trial_data
from murineshiftwork.logic.sounds import StereoSound
from murineshiftwork.namespace.msw_files import msw_file

log = logging.getLogger(__name__)

# All physical ports on the Bpod (1-indexed)
_ALL_PORTS = list(range(1, 9))

# Per-subject level state is stored here
LEVEL_STORE_DIR = Path("~/.murineshiftwork/sequence").expanduser()
_LEGACY_LEVEL_STORE_DIR = Path("~/.murineshiftwork/sequence_automated").expanduser()


class RewardPerturbation:
    """Probabilistic per-poke reward override for probe/deviant-reward experiments.

    Config keys (from task_settings["reward_perturbation"]):
      enabled   bool   activate feature (default False)
      target    str    "position" (0-indexed slot) or "port" (hardware port 1-8)
      distribution  dict[int, list[{amount_ul, probability}]]
                    amount_ul: float µL, or null = nominal level amount
                    probabilities may sum to < 1.0; remainder is implicitly nominal
    """

    enabled: bool

    def __init__(self, config: dict, rng=None):
        self.enabled = bool(config.get("enabled", False))
        self._target = config.get("target", "position")
        self.matched_omission_duration = bool(
            config.get("matched_omission_duration", False)
        )
        self._rng = rng if rng is not None else np.random.default_rng()
        self._distributions: dict[int, tuple[list, list]] = {}
        for k, entries in (config.get("distribution") or {}).items():
            probs = [float(e["probability"]) for e in entries]
            amounts = [e["amount_ul"] for e in entries]  # float or None
            remainder = 1.0 - sum(probs)
            if remainder > 1e-9:
                amounts = amounts + [None]
                probs = probs + [remainder]
            self._distributions[int(k)] = (amounts, probs)

    def draw_trial_rewards(
        self, sequence: list[int], nominal_rewards: list[float]
    ) -> tuple[list[float], list[dict]]:
        """Draw perturbed reward amounts for one trial.

        Returns (delivered_rewards, draw_records).
        draw_records: [{position, port, nominal_ul, delivered_ul, perturbed}]
        """
        delivered: list[float] = []
        records: list[dict] = []
        for i, (port, nominal_ul) in enumerate(zip(sequence, nominal_rewards)):
            key = i if self._target == "position" else port
            if key not in self._distributions:
                delivered.append(nominal_ul)
                records.append(
                    {
                        "position": i,
                        "port": port,
                        "nominal_ul": nominal_ul,
                        "delivered_ul": nominal_ul,
                        "perturbed": False,
                    }
                )
                continue
            amounts, probs = self._distributions[key]
            chosen = amounts[int(self._rng.choice(len(amounts), p=probs))]
            delivered_ul = nominal_ul if chosen is None else float(chosen)
            delivered.append(delivered_ul)
            records.append(
                {
                    "position": i,
                    "port": port,
                    "nominal_ul": nominal_ul,
                    "delivered_ul": delivered_ul,
                    "perturbed": delivered_ul != nominal_ul,
                }
            )
        return delivered, records


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

        # Rolling performance buffers; cleared on every level change.
        # perf_buffer tracks the *selected* scoring metric (ordered or perfect).
        # perf_buffer_perfect always tracks exact-sequence correctness.
        buf_size = task_settings.get("buffer_trials", 10)
        self.perf_buffer = deque(maxlen=buf_size)
        self.perf_buffer_perfect = deque(maxlen=buf_size)

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
        self._session_liquid_ul = 0.0
        self._session_task_trials = 0  # trials with a poke response (scored)
        self._session_no_response_count = 0  # uninitiated / init-timeout trials

        self._perturbation = RewardPerturbation(
            task_settings.get("reward_perturbation") or {}
        )
        self._pending_reward_draw: dict = {}
        self._pending_trial_meta: dict = {}
        self._rng = np.random.default_rng()

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
            if isinstance(v, str | int | float | bool | list | type(None))
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
                "task_trials": self._session_task_trials,
                "no_response_trials": self._session_no_response_count,
            }
        )
        self._push_subject_state(subject, existing)
        self._register_subject(subject)
        log.info(
            "Session end — '%s': level %d, trials %d (%d task, %d no-response)",
            subject,
            self.current_level,
            self.trial_index,
            self._session_task_trials,
            self._session_no_response_count,
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
        with Path(filepath).open() as f:
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
            valve_s_for_ul = self.task_settings.get("valve_s_for_ul")
            if valve_s_for_ul is None:
                raise ValueError(
                    "valve_s_for_ul not in task settings — "
                    "ensure the setup YAML has calibrations.bpod_valve entries."
                )
            self._valve_time_cache[key] = valve_s_for_ul(port, amount_ul)
        return self._valve_time_cache[key]

    def _get_reward_delay_s(self) -> float:
        """Return the reward delay for the current trial.

        If reward_delay_ramp is configured, the delay grows linearly with completed
        task trials up to max_s (useful for gradually introducing temporal uncertainty).
        Otherwise returns the fixed reward_delay_s (default 0.0).
        """
        ramp = self.task_settings.get("reward_delay_ramp") or {}
        if ramp and float(ramp.get("increment_s", 0.0)) > 0:
            start = float(ramp.get("start_s", 0.0))
            increment = float(ramp.get("increment_s", 0.0))
            max_s = float(ramp.get("max_s", start))
            return min(start + increment * self._session_task_trials, max_s)
        return float(self.task_settings.get("reward_delay_s", 0.0))

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

    @staticmethod
    def _dedup_pokes(trial_data: dict) -> list[int]:
        """Sort all PortIn events by time and remove consecutive duplicate ports."""
        events = trial_data.get("Events timestamps", {})
        raw: list[tuple[float, int]] = []
        for port in range(1, 9):
            for t in events.get(f"Port{port}In", []):
                raw.append((t, port))
        raw.sort()
        deduped: list[int] = []
        for _, port in raw:
            if not deduped or deduped[-1] != port:
                deduped.append(port)
        return deduped

    def _score_sequence_matlab(self, trial_data: dict) -> bool:
        """'Ordered' metric: sequence appears as a contiguous subsequence.

        Mirrors UpdateLevel.m strfind logic — extra pokes between or around the
        template are allowed as long as the template occurs somewhere in the
        deduped poke stream.
        """
        deduped = self._dedup_pokes(trial_data)
        if not deduped:
            return False
        template = list(self.sequence)
        n = len(template)
        return any(deduped[i : i + n] == template for i in range(len(deduped) - n + 1))

    def _score_sequence_perfect(self, trial_data: dict) -> bool:
        """'Perfect' metric: exact sequence, no extra pokes anywhere.

        The deduped poke stream must equal the template exactly — no extra pokes
        before, between, or after the sequence steps.
        """
        deduped = self._dedup_pokes(trial_data)
        return deduped == list(self.sequence)

    def _extract_poke_events(self, trial_data: dict) -> list:
        """Return all port-in events sorted by time from trial start (t=0 = state machine start)."""
        events = trial_data.get("Events timestamps", {})
        raw = []
        for port in range(1, 9):
            for t in events.get(f"Port{port}In", []):
                raw.append({"port": port, "time": round(t, 4)})
        raw.sort(key=lambda x: x["time"])
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

        # Reward perturbation: draw per-poke amounts, overriding nominal level amounts
        nominal_rewards = list(rewards)
        if self._perturbation.enabled:
            delivered, draws = self._perturbation.draw_trial_rewards(
                self.sequence, nominal_rewards
            )
            self._pending_reward_draw = {
                "nominal": nominal_rewards,
                "delivered": delivered,
                "draws": draws,
            }
            rewards = delivered
        else:
            self._pending_reward_draw = {}

        # Reward delay: fixed gap between correct poke and valve opening
        current_delay_s = self._get_reward_delay_s()
        matched_omission = self._perturbation.matched_omission_duration

        # Non-contingent reward: free delivery before the sequence begins
        free_reward_prob = float(self.task_settings.get("free_reward_probability", 0.0))
        free_reward_ul = float(self.task_settings.get("free_reward_ul", 1.8))
        free_port_cfg = self.task_settings.get("free_reward_port")
        free_port = int(free_port_cfg) if free_port_cfg else self.sequence[-1]
        give_free = (
            free_reward_prob > 0 and float(self._rng.random()) < free_reward_prob
        )
        self._pending_trial_meta = {
            "delay_s": current_delay_s,
            "free_reward_given": give_free,
            "free_reward_ul": free_reward_ul if give_free else 0.0,
        }

        # strict_sequence=True: any wrong poke immediately triggers punish (strict mode)
        # strict_sequence=False (default): wrong pokes ignored; only timeout or correct
        # poke causes a state transition — equivalent to the original MATLAB behaviour
        strict = self.task_settings.get("strict_sequence", False)
        init_timeout = float(self.task_settings.get("init_port_timeout_s", 0.0))

        sma = StateMachine(bpod=self.bpod)

        # Free-reward state: dispense before sequence starts, no BNC marker
        if give_free:
            free_valve_time = self._get_valve_time(free_port, free_reward_ul)
            sma.add_state(
                state_name="free_reward_state",
                state_timer=max(free_valve_time, 0.001),
                state_change_conditions={Bpod.Events.Tup: "wait_poke_0"},
                output_actions=[(Bpod.OutputChannels.Valve, free_port)]
                if free_valve_time > 0
                else [],
            )

        for i, (port, reward_ul, led_val, nominal_ul) in enumerate(
            zip(self.sequence, rewards, leds, nominal_rewards)
        ):
            led_pwm = self._scale_led(led_val)
            pwm_ch = getattr(Bpod.OutputChannels, f"PWM{port}")
            valve_time = self._get_valve_time(port, reward_ul)
            next_state_after_reward = (
                f"wait_poke_{i + 1}" if i < self.n_pokes - 1 else "exit_seq"
            )
            # With a delay, a correct poke goes to a delay state before the reward state
            correct_next = (
                f"delay_poke_{i}" if current_delay_s > 0 else f"reward_poke_{i}"
            )

            if i == 0:
                # First poke: Tup must only be present when state_timer > 0 — at
                # timer=0 it fires immediately and must not be in state_change_conditions.
                wait_conditions = {
                    getattr(Bpod.Events, f"Port{port}In"): correct_next,
                }
                if init_timeout > 0:
                    wait_conditions[Bpod.Events.Tup] = "punish"
                    state_timer = init_timeout
                else:
                    state_timer = 0
                if strict:
                    for p in _ALL_PORTS:
                        if p != port:
                            wait_conditions[getattr(Bpod.Events, f"Port{p}In")] = (
                                "punish"
                            )
            elif strict:
                wait_conditions = {Bpod.Events.Tup: "punish"}
                for p in _ALL_PORTS:
                    event = getattr(Bpod.Events, f"Port{p}In")
                    wait_conditions[event] = correct_next if p == port else "punish"
                state_timer = response_window
            else:
                wait_conditions = {
                    Bpod.Events.Tup: "punish",
                    getattr(Bpod.Events, f"Port{port}In"): correct_next,
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

            # Delay state: blank gap between correct poke and valve opening
            if current_delay_s > 0:
                sma.add_state(
                    state_name=f"delay_poke_{i}",
                    state_timer=current_delay_s,
                    state_change_conditions={Bpod.Events.Tup: f"reward_poke_{i}"},
                    output_actions=[],
                )

            # Matched omission: hold the reward state open for the nominal valve
            # duration so the negative RPE is anchored to the expected reward time.
            if matched_omission and reward_ul == 0.0 and nominal_ul > 0.0:
                reward_state_timer = max(self._get_valve_time(port, nominal_ul), 0.001)
            else:
                reward_state_timer = max(valve_time, 0.001)

            # Open valve (if reward > 0) and play chirp
            reward_actions = []
            if valve_time > 0:
                reward_actions.append((Bpod.OutputChannels.Valve, port))
            if self.task_settings.get("reward_sound", True):
                reward_actions.append(("SoftCode", self.sound_reward_code))

            sma.add_state(
                state_name=f"reward_poke_{i}",
                state_timer=reward_state_timer,
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

        # Uninitiated trials (init timeout, no pokes) must not affect buffers or
        # level evaluation in either direction.
        poke_events = self._extract_poke_events(trial_data)
        if not poke_events:
            self.last_outcome = "no_response"
            self._session_no_response_count += 1
            self._pending_reward_draw = {}
            _meta_nr = self._pending_trial_meta
            self._pending_trial_meta = {}
            # Free reward may still have been delivered at trial start
            _free_ul_nr = _meta_nr.get("free_reward_ul", 0.0)
            self._session_liquid_ul += _free_ul_nr
            trial_data["info"] = {
                "trial_type": "task",
                "trial_index": trial_index,
                "level": self.current_level,
                "outcome": "no_response",
                "is_perfect": False,
                "is_ordered": False,
                "scoring_metric": self.task_settings.get("scoring_metric", "ordered"),
                "reward_delay_s": _meta_nr.get("delay_s", 0.0),
                "free_reward_given": _meta_nr.get("free_reward_given", False),
                "poke_events": [],
                "transition_times": [],
                "sequence_duration_s": None,
                "reward_count_trial": 0,
                "liquid_ul_trial": round(_free_ul_nr, 2),
                "liquid_ul_cumulative": round(self._session_liquid_ul, 2),
                "perf_buffer_mean": float(np.mean(self.perf_buffer))
                if self.perf_buffer
                else 0.0,
                "perf_perfect_mean": float(np.mean(self.perf_buffer_perfect))
                if self.perf_buffer_perfect
                else 0.0,
            }
            trial_data["analysis"] = {}
            self.trial_data.append(trial_data)
            _t = trial_data.get("Trial start timestamp", 0)
            logging.info(
                "[T=%5.1f min] Trial %4d | Lvl %2d    | no_resp   | Perf — (no change)",
                _t / 60,
                trial_index,
                self.current_level,
            )
            return

        # Score with both metrics; selected metric drives level advancement.
        # perf_buffer_perfect always tracks exact-match rate regardless of setting.
        scoring_metric = self.task_settings.get("scoring_metric", "ordered")
        is_ordered = self._score_sequence_matlab(trial_data)
        is_perfect = self._score_sequence_perfect(trial_data)
        is_correct = is_perfect if scoring_metric == "perfect" else is_ordered
        self.last_outcome = "correct" if is_correct else "incorrect"

        # Track buffers
        self.perf_buffer.append(1 if is_correct else 0)
        self.perf_buffer_perfect.append(1 if is_perfect else 0)

        # Snapshot level and params for this trial BEFORE any level change
        trial_level = self.current_level
        params = self._get_level_params()
        perf = float(np.mean(self.perf_buffer)) if self.perf_buffer else 0.0
        perf_perfect = (
            float(np.mean(self.perf_buffer_perfect))
            if self.perf_buffer_perfect
            else 0.0
        )

        # Consume pending draw and trial metadata set by draw_next_trial
        _pert = self._pending_reward_draw
        self._pending_reward_draw = {}
        _meta = self._pending_trial_meta
        self._pending_trial_meta = {}
        _effective_rewards = list(_pert.get("delivered") or params["rewards"])
        _free_ul = _meta.get("free_reward_ul", 0.0)

        # Count rewards/water actually dispensed this trial
        st = trial_data["States timestamps"]
        rewards_this_trial = 0
        liquid_this_trial = 0.0
        for i in range(self.n_pokes):
            rkey = f"reward_poke_{i}"
            if (
                rkey in st
                and not np.isnan(np.array(st[rkey][0])).all()
                and _effective_rewards[i] > 0
            ):
                rewards_this_trial += 1
                liquid_this_trial += _effective_rewards[i]
        self._session_reward_count += rewards_this_trial
        self._session_liquid_ul += liquid_this_trial + _free_ul
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
            "is_perfect": is_perfect,
            "is_ordered": is_ordered,
            "sequence": self.sequence,
            "scoring_metric": scoring_metric,
            "reward_amounts": _effective_rewards,
            "led_intensities": params["leds"],
            "perf_buffer_mean": perf,
            "perf_perfect_mean": perf_perfect,
            "perf_buffer_n": len(self.perf_buffer),
            "reward_delay_s": _meta.get("delay_s", 0.0),
            "free_reward_given": _meta.get("free_reward_given", False),
            "reward_count_trial": rewards_this_trial,
            "liquid_ul_trial": round(liquid_this_trial + _free_ul, 2),
            "liquid_ul_cumulative": round(self._session_liquid_ul, 2),
            "poke_events": poke_events,
            "transition_times": transition_times,
            "sequence_duration_s": sequence_duration_s,
        }
        if _pert.get("draws"):
            trial_data["info"]["reward_amounts_nominal"] = _pert["nominal"]
            trial_data["info"]["reward_perturbation_applied"] = any(
                d["perturbed"] for d in _pert["draws"]
            )
            trial_data["info"]["reward_perturbation_draws"] = _pert["draws"]
        trial_data["analysis"] = {}
        self.trial_data.append(trial_data)
        self._session_task_trials += 1

        _t = trial_data.get("Trial start timestamp", 0)
        lvl_arrow = (
            f"→{self.current_level}" if self.current_level != trial_level else "  "
        )
        n_correct = int(sum(self.perf_buffer))
        n_buf = len(self.perf_buffer)
        logging.info(
            "[T=%5.1f min] Trial %4d | Lvl %2d%-3s | %s | Perf %.2f (%d/%d) | R:%d %.1fuL | Total:%.1fuL",
            _t / 60,
            trial_index,
            trial_level,
            lvl_arrow,
            "CORRECT  " if is_correct else "incorrect",
            perf,
            n_correct,
            n_buf,
            rewards_this_trial,
            liquid_this_trial,
            self._session_liquid_ul,
        )

    def _update_level(self):
        # Mirrors MATLAB UpdateLevel.m exactly: single progression_threshold,
        # strictly-greater comparison (> not >=), buffer must be full.
        buf = self.perf_buffer
        n_levels = len(self.levels_df)
        prog_thresh = self.task_settings.get("progression_threshold", 0.9)
        reg_thresh = self.task_settings.get("regression_threshold", 0.2)

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
        self.perf_buffer_perfect.clear()
        self._save_level()
        self._register_subject(self.task_settings["subject"])
        log.info(f"Level advanced: {old} → {self.current_level}")

    def _regress_level(self):
        old = self.current_level
        self.current_level = max(self.current_level - 1, 1)
        self.perf_buffer.clear()
        self.perf_buffer_perfect.clear()
        self._save_level()
        self._register_subject(self.task_settings["subject"])
        log.info(f"Level regressed: {old} → {self.current_level}")

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def save(self):
        save_trial_data(self.trial_data, msw_file(self.save_path, "df.jsonl"))

    def __del__(self):
        if hasattr(self, "save_path"):
            self.save()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()
