"""Unit tests for the sequence task: state machine logic, level loading, poke handling."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pytest.importorskip("ttl_barcoder")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LEVELS_COLS = [
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


def _make_levels_df(n=5):
    """Minimal levels table: n identical rows with 3 µL rewards and 2 s windows."""
    row = [3.0, 3.0, 3.0, 3.0, 3.0, 50.0, 50.0, 50.0, 50.0, 50.0, 2.0]
    return pd.DataFrame([row] * n, columns=_LEVELS_COLS)


def _make_tc(sequence=None, task_settings=None, current_level=1, n_levels=5):
    """Build a TaskControl bypassing __init__ (no Bpod, no file I/O)."""
    from murineshiftwork.tasks.sequence.task_objects import TaskControl

    seq = sequence if sequence is not None else [2, 1, 6, 3, 7]
    settings = {
        "subject": "mouse001",
        "start_level": 1,
        "buffer_trials": 10,
        "min_response_window_s": 2.0,
        "punish_duration": 0.5,
        "iti_duration": 0.4,
        "reward_sound": False,
        "strict_sequence": False,
        "HARDWARE_BNC_TRIAL_START": 1,
        "init_port_timeout_s": 10.0,
    }
    if task_settings:
        settings.update(task_settings)

    from collections import deque

    tc = object.__new__(TaskControl)
    tc.sequence = seq
    tc.n_pokes = len(seq)
    tc.task_settings = settings
    tc.current_level = current_level
    tc._valve_time_cache = {}
    tc.levels_df = _make_levels_df(n_levels)
    tc._session_start_level = current_level
    tc.perf_buffer = deque(maxlen=settings.get("buffer_trials", 10))
    tc.perf_buffer_perfect = deque(maxlen=settings.get("buffer_trials", 10))
    tc._session_reward_count = 0
    tc._session_liquid_ul = 0.0
    tc._session_task_trials = 0
    tc._session_no_response_count = 0

    import numpy as np
    from murineshiftwork.tasks.sequence.task_objects import RewardPerturbation

    tc._perturbation = RewardPerturbation(settings.get("reward_perturbation") or {})
    tc._pending_reward_draw = {}
    tc._pending_trial_meta = {}
    tc._rng = np.random.default_rng(42)

    # Valve calibration injected by CLI/agent: always return 0.05 s
    tc.task_settings["valve_s_for_ul"] = lambda port, ul: 0.05

    tc.sound = MagicMock()
    tc.sound_reward_code = 0
    tc.bpod = MagicMock()
    tc.bnc_channel = "BNC1"
    tc.trial_data = []
    tc.save_path = MagicMock()
    tc.save = MagicMock()  # prevent __del__ from writing real files
    return tc


def _build_sma(tc):
    """Call draw_next_trial with Bpod and StateMachine patched to pure strings."""
    states = {}

    class FakeSMA:
        def add_state(
            self, state_name, state_timer, state_change_conditions, output_actions
        ):
            states[state_name] = {
                "timer": state_timer,
                "conditions": state_change_conditions,
                "actions": output_actions,
            }

    class FakeBpodEvents:
        Tup = "Tup"

        def __getattr__(self, name):
            return name  # e.g. "Port1In"

    class FakeBpodOutputChannels:
        Valve = "Valve"

        def __getattr__(self, name):
            return name  # e.g. "PWM1", "BNC1"

    class FakeBpod:
        Events = FakeBpodEvents()
        OutputChannels = FakeBpodOutputChannels()

    with (
        patch(
            "murineshiftwork.tasks.sequence.task_objects.StateMachine",
            return_value=FakeSMA(),
        ),
        patch("murineshiftwork.tasks.sequence.task_objects.Bpod", FakeBpod),
    ):
        tc.draw_next_trial()

    return states


# ---------------------------------------------------------------------------
# Poke-handling mode tests
# ---------------------------------------------------------------------------


class TestDrawNextTrialLenientMode:
    """strict_sequence=False (default): wrong pokes ignored, only Tup and correct port transition."""

    def test_wait_state_has_only_tup_and_correct_port(self):
        tc = _make_tc()
        states = _build_sma(tc)

        conds = states["wait_poke_0"]["conditions"]
        # Only two transitions: timeout and the correct port
        assert len(conds) == 2
        assert "Tup" in conds
        assert conds["Tup"] == "punish"
        assert f"Port{tc.sequence[0]}In" in conds
        assert conds[f"Port{tc.sequence[0]}In"] == "reward_poke_0"

    def test_wrong_ports_absent_from_wait_conditions(self):
        tc = _make_tc(sequence=[2, 1, 6, 3, 7])
        states = _build_sma(tc)

        # For each wait state, no wrong-port key should be present
        for i, port in enumerate(tc.sequence):
            conds = states[f"wait_poke_{i}"]["conditions"]
            for p in range(1, 9):
                if p != port:
                    assert f"Port{p}In" not in conds, (
                        f"wait_poke_{i}: wrong port {p} should not be in conditions"
                    )

    def test_last_reward_goes_to_exit_seq(self):
        tc = _make_tc()
        states = _build_sma(tc)
        last = f"reward_poke_{tc.n_pokes - 1}"
        assert states[last]["conditions"] == {"Tup": "exit_seq"}

    def test_punish_and_exit_seq_states_present(self):
        tc = _make_tc()
        states = _build_sma(tc)
        assert "punish" in states
        assert "exit_seq" in states
        assert states["punish"]["conditions"] == {"Tup": "exit_seq"}
        assert states["exit_seq"]["conditions"] == {"Tup": "exit"}


class TestDrawNextTrialStrictMode:
    """strict_sequence=True: any wrong poke immediately goes to punish."""

    def test_all_wrong_ports_map_to_punish(self):
        tc = _make_tc(task_settings={"strict_sequence": True})
        states = _build_sma(tc)

        for i, port in enumerate(tc.sequence):
            conds = states[f"wait_poke_{i}"]["conditions"]
            for p in range(1, 9):
                key = f"Port{p}In"
                if p == port:
                    assert conds[key] == f"reward_poke_{i}"
                else:
                    assert conds[key] == "punish", (
                        f"wait_poke_{i}: port {p} should map to punish in strict mode"
                    )

    def test_tup_maps_to_punish(self):
        tc = _make_tc(task_settings={"strict_sequence": True})
        states = _build_sma(tc)
        assert states["wait_poke_0"]["conditions"]["Tup"] == "punish"


# ---------------------------------------------------------------------------
# Sequence flexibility tests
# ---------------------------------------------------------------------------


class TestSequenceFlexibility:
    def test_three_poke_sequence(self):
        tc = _make_tc(sequence=[1, 3, 5])
        states = _build_sma(tc)
        assert "wait_poke_0" in states
        assert "wait_poke_1" in states
        assert "wait_poke_2" in states
        assert "wait_poke_3" not in states
        assert states["reward_poke_2"]["conditions"] == {"Tup": "exit_seq"}

    def test_sequence_with_repeated_port(self):
        """A port appearing twice in the sequence must create independent states."""
        tc = _make_tc(sequence=[2, 1, 6, 3, 7, 3])  # port 3 at positions 3 and 5
        states = _build_sma(tc)
        assert len([k for k in states if k.startswith("wait_poke_")]) == 6
        # Both positions for port 3 must point to their own reward state
        assert states["wait_poke_3"]["conditions"]["Port3In"] == "reward_poke_3"
        assert states["wait_poke_5"]["conditions"]["Port3In"] == "reward_poke_5"
        # Final reward goes to exit
        assert states["reward_poke_5"]["conditions"] == {"Tup": "exit_seq"}

    def test_six_poke_sequence_rewards_padded(self):
        """Sequences longer than 5 pokes use the last level-row reward for extra pokes."""
        tc = _make_tc(sequence=[1, 2, 3, 4, 5, 6])
        states = _build_sma(tc)
        # All 6 wait and reward states must exist
        for i in range(6):
            assert f"wait_poke_{i}" in states
            assert f"reward_poke_{i}" in states


# ---------------------------------------------------------------------------
# Level loading tests
# ---------------------------------------------------------------------------


class TestLoadLevel:
    def _make_tc_for_level(self, start_level, n_levels=50):
        tc = _make_tc(task_settings={"start_level": start_level}, n_levels=n_levels)
        return tc

    def test_start_level_respected(self):
        """_load_level returns task_settings['start_level'] directly."""
        tc = self._make_tc_for_level(start_level=30)
        assert tc._load_level("mouse001") == 30

    def test_start_level_clamped_to_table_length(self):
        tc = self._make_tc_for_level(start_level=99, n_levels=10)
        assert tc._load_level("mouse001") == 10

    def test_start_level_clamped_to_minimum_1(self):
        tc = self._make_tc_for_level(start_level=0)
        assert tc._load_level("mouse001") == 1

    def test_json_store_does_not_override_start_level(self, monkeypatch):
        """JSON store level is ignored; task_settings['start_level'] wins."""
        from murineshiftwork.tasks.sequence.task_objects import TaskControl

        monkeypatch.setattr(
            TaskControl, "_fetch_subject_state", lambda self, s: {"level": 5}
        )
        tc = self._make_tc_for_level(start_level=30)
        # Even though JSON says 5, start_level=30 wins
        assert tc._load_level("mouse001") == 30

    def test_default_start_level_is_1(self):
        tc = _make_tc()  # no explicit start_level override
        assert tc._load_level("mouse001") == 1


# ---------------------------------------------------------------------------
# Level progression / regression tests
# ---------------------------------------------------------------------------


class TestLevelProgression:
    def test_advance_level(self):
        from collections import deque

        tc = _make_tc(current_level=3, n_levels=10)
        tc.perf_buffer = deque([1] * 10, maxlen=10)
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        tc._advance_level()
        assert tc.current_level == 4

    def test_no_advance_at_max_level(self):
        from collections import deque

        tc = _make_tc(current_level=5, n_levels=5)
        tc.perf_buffer = deque([1] * 10, maxlen=10)
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        tc._advance_level()
        assert tc.current_level == 5

    def test_regress_level(self):
        from collections import deque

        tc = _make_tc(current_level=3, n_levels=10)
        tc.perf_buffer = deque([0] * 10, maxlen=10)
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        tc._regress_level()
        assert tc.current_level == 2

    def test_prevent_regression_below_session_start(self):
        from collections import deque

        tc = _make_tc(
            current_level=5,
            n_levels=10,
            task_settings={"prevent_regression_below_start": True},
        )
        tc._session_start_level = 5
        tc.perf_buffer = deque([0] * 10, maxlen=10)
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        tc._update_level()
        assert tc.current_level == 5  # not regressed below session start

    def test_regression_fires_when_prevent_is_false(self):
        """0% perf at level 10 must regress to 9 when prevent_regression_below_start=False."""
        from collections import deque

        tc = _make_tc(
            current_level=10,
            n_levels=10,
            task_settings={
                "prevent_regression_below_start": False,
                "regression_threshold": 0.2,
            },
        )
        tc._session_start_level = 10
        tc.perf_buffer = deque([0] * 10, maxlen=10)
        tc.perf_buffer_perfect = deque(maxlen=10)
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        tc._update_level()
        assert tc.current_level == 9

    def test_level_1_advances_on_full_buffer(self):
        """Level 1 must advance when buffer is full and perf > threshold."""
        from collections import deque

        tc = _make_tc(current_level=1, n_levels=10)
        tc.perf_buffer = deque([1] * 10, maxlen=10)
        tc.perf_buffer_perfect = deque(maxlen=10)
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        tc._update_level()
        assert tc.current_level == 2

    def test_level_1_no_regress_below_floor(self):
        """Level 1 must never regress below 1."""
        from collections import deque

        tc = _make_tc(
            current_level=1,
            n_levels=10,
            task_settings={"prevent_regression_below_start": False},
        )
        tc._session_start_level = 1
        tc.perf_buffer = deque([0] * 10, maxlen=10)
        tc.perf_buffer_perfect = deque(maxlen=10)
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        tc._update_level()
        assert tc.current_level == 1


# ---------------------------------------------------------------------------
# No-response trial tests
# ---------------------------------------------------------------------------


def _make_trial_data(port_events: dict | None = None) -> dict:
    """Minimal trial_data dict mimicking bpod export."""
    return {
        "Trial start timestamp": 60.0,
        "States timestamps": {
            "wait_poke_0": [[0.0, 10.0]],
            "punish": [[10.0, 10.5]],
            "exit_seq": [[10.5, 10.9]],
        },
        "Events timestamps": port_events or {},
    }


class TestNoResponseTrials:
    def _make_full_tc(self):
        from collections import deque

        tc = _make_tc(current_level=5, n_levels=10)
        tc._session_start_level = 5
        tc.perf_buffer = deque(maxlen=10)
        tc.perf_buffer_perfect = deque(maxlen=10)
        tc._session_reward_count = 0
        tc._session_liquid_ul = 0.0
        tc._save_level = MagicMock()
        tc._register_subject = MagicMock()
        return tc

    def test_no_response_outcome(self):
        tc = self._make_full_tc()
        trial_data = _make_trial_data()
        tc.update(trial_index=0, trial_data=trial_data)
        assert tc.last_outcome == "no_response"

    def test_no_response_does_not_fill_perf_buffer(self):
        tc = self._make_full_tc()
        trial_data = _make_trial_data()
        tc.update(trial_index=0, trial_data=trial_data)
        assert len(tc.perf_buffer) == 0
        assert len(tc.perf_buffer_perfect) == 0

    def test_no_response_does_not_change_level(self):
        """10 consecutive no-response trials must not regress level."""

        tc = self._make_full_tc()
        tc.task_settings["prevent_regression_below_start"] = False
        tc.task_settings["regression_threshold"] = 0.2
        for i in range(15):
            tc.update(trial_index=i, trial_data=_make_trial_data())
        assert tc.current_level == 5
        assert len(tc.perf_buffer) == 0

    def test_no_response_info_fields(self):
        tc = self._make_full_tc()
        trial_data = _make_trial_data()
        tc.update(trial_index=3, trial_data=trial_data)
        info = trial_data["info"]
        assert info["outcome"] == "no_response"
        assert info["trial_type"] == "task"
        assert info["poke_events"] == []
        assert info["reward_count_trial"] == 0
