"""Simulated Bpod — drop-in replacement for BpodFactory that logs all commands.

Enables hardware-free testing and CI coverage of tasks and action drivers without
any USB devices connected.  All state-machine calls return success; manual_override
calls are recorded in self.calls for assertion in tests.

SimBpod.hardware is pre-populated to match a standard 4-port Bpod so that
StateMachine(bpod=sim_bpod) and sma.add_state(...) work without any serial
connection.  The hardware configuration represents:
  outputs: SoftCode, PWM1-4, Valve1-4, BNC1-2, Wire1-2
  inputs:  SoftCode1-15, Port1-4In/Out/Lick, BNC1-2, Wire1-2, Tup

Usage:
    from murineshiftwork.hardware.bpod.sim import SimBpod

    bpod = SimBpod()
    bpod.open()
    # ... use in tasks or BpodActionDriver ...
    assert ("manual_override", ...) in bpod.calls
"""
import logging


def _build_sim_hardware():
    """Return a pre-populated Hardware matching a standard 4-port Bpod.

    Populated enough that StateMachine(bpod=...) and add_state() with Valve,
    BNC, SoftCode, and Tup events all work without a serial connection.
    """
    from pybpodapi.bpod.hardware.hardware import Hardware
    h = Hardware()
    h.max_states = 255
    h.n_conditions = 5
    h.n_global_counters = 5
    h.n_global_timers = 5
    h.max_serial_events = 15
    h.firmware_version = 22
    h.machine_type = 1
    h.cycle_period = 100
    # 4 behavior ports (P), USB (X), 2 BNC (B), 2 Wire (W) — no UART modules
    h.inputs = ["X", "P", "P", "P", "P", "B", "B", "W", "W"]
    h.inputs_enabled = [1] * len(h.inputs)
    # USB (X), 4 PWM ports (P), 4 Valves (V), 2 BNC (B), 2 Wire (W)
    h.outputs = ["X", "P", "P", "P", "P", "V", "V", "V", "V", "B", "B", "W", "W"]
    h.n_uart_channels = 0
    h.setup(modules=[])
    return h


class SimBpod:
    """Simulated BpodFactory: logs all interactions, returns success.

    Mirrors the BpodFactory public API so it can be injected wherever a real
    BpodFactory is expected (TaskProcess bpod= kwarg, BpodActionDriver, etc.).
    """

    def __init__(self, **kwargs) -> None:
        self.calls: list = []
        self._softcode_handler = None
        self.hardware = _build_sim_hardware()

    # Context manager

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close_safely()

    # Connection lifecycle

    def open(self, **kwargs) -> None:
        logging.debug("[SIM] Bpod.open()")
        self.calls.append(("open",))

    def close_safely(self) -> None:
        logging.debug("[SIM] Bpod.close_safely()")
        self.calls.append(("close_safely",))

    def stop_trial(self) -> None:
        logging.debug("[SIM] Bpod.stop_trial()")
        self.calls.append(("stop_trial",))

    # Softcode handler property (mirrors BpodFactory proxy)

    @property
    def softcode_handler_function(self):
        return self._softcode_handler

    @softcode_handler_function.setter
    def softcode_handler_function(self, value):
        self._softcode_handler = value

    # State machine

    def send_state_machine(self, sma) -> None:
        state_names = getattr(sma, "state_names", "?")
        logging.debug(f"[SIM] Bpod.send_state_machine(states={state_names})")
        self.calls.append(("send_state_machine", sma))

    def run_state_machine(self, sma) -> bool:
        logging.debug("[SIM] Bpod.run_state_machine() → True")
        self.calls.append(("run_state_machine", sma))
        return True

    # Firmware override

    def manual_override(
        self, channel_type, channel_name, channel_number, value
    ) -> None:
        logging.debug(
            f"[SIM] Bpod.manual_override("
            f"type={channel_type}, name={channel_name}, "
            f"ch={channel_number}, val={value})"
        )
        self.calls.append(
            ("manual_override", channel_type, channel_name, channel_number, value)
        )

    # Helpers for test assertions

    def override_calls(self) -> list:
        """Return only the manual_override call tuples."""
        return [c for c in self.calls if c[0] == "manual_override"]

    def sma_run_count(self) -> int:
        """Number of times run_state_machine was called."""
        return sum(1 for c in self.calls if c[0] == "run_state_machine")
