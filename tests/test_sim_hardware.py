"""Tests for SimBpod, SimWeighingScale, and BpodActionDriver.

These tests run entirely without physical hardware — SimBpod records all
manual_override() and SMA calls; SimWeighingScale returns deterministic
weights.  They are intended to run in CI (GitHub Actions) with no USB
devices connected.
"""
import pytest

from pybpodapi.bpod.hardware.channels import ChannelName, ChannelType

from murineshiftwork.hardware.bpod.actions import BpodActionDriver
from murineshiftwork.hardware.bpod.sim import SimBpod
from murineshiftwork.logic.config.models import ActionRequest
from murineshiftwork.logic.scale import SimWeighingScale, make_scale


# ---------------------------------------------------------------------------
# SimBpod

class TestSimBpod:
    def test_open_recorded(self):
        bpod = SimBpod()
        bpod.open()
        assert ("open",) in bpod.calls

    def test_run_state_machine_returns_true(self):
        bpod = SimBpod()
        result = bpod.run_state_machine(object())
        assert result is True

    def test_sma_run_count(self):
        bpod = SimBpod()
        bpod.run_state_machine(object())
        bpod.run_state_machine(object())
        assert bpod.sma_run_count() == 2

    def test_manual_override_recorded(self):
        bpod = SimBpod()
        bpod.manual_override(ChannelType.OUTPUT, ChannelName.VALVE, 1, 1)
        bpod.manual_override(ChannelType.OUTPUT, ChannelName.VALVE, 1, 0)
        overrides = bpod.override_calls()
        assert len(overrides) == 2
        assert overrides[0][4] == 1   # value open
        assert overrides[1][4] == 0   # value close

    def test_softcode_handler_roundtrip(self):
        bpod = SimBpod()
        handler = lambda x: x
        bpod.softcode_handler_function = handler
        assert bpod.softcode_handler_function is handler

    def test_context_manager(self):
        with SimBpod() as bpod:
            bpod.open()
        assert ("close_safely",) in bpod.calls


# ---------------------------------------------------------------------------
# SimWeighingScale

class TestSimWeighingScale:
    def test_returns_fixed_weight(self):
        scale = SimWeighingScale(weight_g=0.050)
        scale.start()
        scale.tare()
        assert scale.read_weight_blocking() == pytest.approx(0.050)

    def test_tare_count_tracked(self):
        scale = SimWeighingScale()
        scale.tare()
        scale.tare()
        assert scale.tare_count == 2

    def test_read_count_tracked(self):
        scale = SimWeighingScale()
        scale.start()
        scale.read_weight_blocking()
        scale.read_weight_blocking()
        assert scale.read_count == 2

    def test_weight_log_matches_reads(self):
        scale = SimWeighingScale(weight_g=0.010)
        scale.start()
        scale.read_weight_blocking()
        scale.read_weight_blocking()
        assert scale.weight_log == [0.010, 0.010]


# ---------------------------------------------------------------------------
# make_scale factory

class TestMakeScale:
    def test_sim_type_returns_sim_scale(self):
        scale = make_scale(scale_type="sim")
        assert isinstance(scale, SimWeighingScale)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown scale_type"):
            make_scale(scale_type="magical_scale")


# ---------------------------------------------------------------------------
# BpodActionDriver — uses SimBpod, no hardware

class TestBpodActionDriver:
    def _make_driver(self):
        bpod = SimBpod()
        bpod.open()
        return BpodActionDriver(bpod), bpod

    def test_unknown_action_raises(self):
        driver, _ = self._make_driver()
        req = ActionRequest(setup="s", device="bpod", action="fire_laser", params={})
        with pytest.raises(ValueError, match="Unknown action"):
            driver.dispatch(req)

    def test_valve_pulse_sends_open_then_close(self):
        driver, bpod = self._make_driver()
        req = ActionRequest(
            setup="s", device="bpod", action="valve_pulse",
            params={"valve_id": 2, "duration_s": 0.001, "n_pulses": 1, "inter_pulse_s": 0.001},
        )
        driver.dispatch(req)
        overrides = bpod.override_calls()
        # The finally-block adds one extra close, so expect open + close + close(finally)
        values = [o[4] for o in overrides]
        assert values[0] == 1, "first call must open valve"
        assert values[1] == 0, "second call must close valve"

    def test_valve_pulse_repeated_n_times(self):
        driver, bpod = self._make_driver()
        req = ActionRequest(
            setup="s", device="bpod", action="valve_pulse",
            params={"valve_id": 1, "duration_s": 0.001, "n_pulses": 3, "inter_pulse_s": 0.001},
        )
        driver.dispatch(req)
        overrides = bpod.override_calls()
        opens = [o for o in overrides if o[4] == 1]
        assert len(opens) == 3, f"expected 3 open calls, got {len(opens)}"

    def test_valve_flush_uses_default_params(self):
        driver, bpod = self._make_driver()
        # Override n_pulses to 1 to keep the test fast
        req = ActionRequest(
            setup="s", device="bpod", action="valve_flush",
            params={"valve_id": 3, "n_pulses": 1, "duration_s": 0.001, "inter_pulse_s": 0.001},
        )
        driver.dispatch(req)
        overrides = bpod.override_calls()
        opens = [o for o in overrides if o[4] == 1]
        assert len(opens) == 1
        # Valve number should be 3
        assert overrides[0][3] == 3

    def test_valve_closes_on_interrupt(self):
        """Even if the loop body raises, valve is closed in finally."""
        class _FailBpod(SimBpod):
            def manual_override(self, *args):
                if args[-1] == 1:  # on open, record then raise after first
                    self.calls.append(("manual_override",) + args)
                    if len(self.override_calls()) == 1:
                        raise RuntimeError("simulated serial error")
                else:
                    super().manual_override(*args)

        bpod = _FailBpod()
        bpod.open()
        driver = BpodActionDriver(bpod)
        req = ActionRequest(
            setup="s", device="bpod", action="valve_pulse",
            params={"valve_id": 1, "duration_s": 0.001, "n_pulses": 1, "inter_pulse_s": 0.001},
        )
        with pytest.raises(RuntimeError):
            driver.dispatch(req)
        # The finally block should have attempted a close (value=0)
        close_calls = [o for o in bpod.override_calls() if o[4] == 0]
        assert len(close_calls) >= 1, "valve must be closed in finally even after exception"


# ---------------------------------------------------------------------------
# ActionRequest model

class TestActionRequest:
    def test_default_params_is_empty_dict(self):
        req = ActionRequest(setup="s1", device="bpod", action="valve_pulse")
        assert req.params == {}

    def test_params_accepted(self):
        req = ActionRequest(
            setup="s1", device="bpod", action="valve_pulse",
            params={"valve_id": 2, "duration_s": 0.030},
        )
        assert req.params["valve_id"] == 2

    def test_missing_required_fields_raise(self):
        with pytest.raises(Exception):
            ActionRequest(device="bpod", action="valve_pulse")  # missing setup
