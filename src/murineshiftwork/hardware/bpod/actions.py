"""One-shot hardware action drivers dispatched from an ActionRequest.

Phase 1: BpodActionDriver is instantiated with an already-open BpodFactory and
called from the CLI (blocking, fresh connection, no concurrent state machine).

Phase 2 (ControllerSession): same dispatch() entry point — ControllerSession
owns the BpodFactory, acquires bpod._write_lock before calling dispatch(), and
the action injects manual_override() calls at firmware level without interrupting
the running state machine.

Note: valve actions use bpod.manual_override() directly — NOT the state machine.
The SMA approach (make_sma_for_drop_of_water) is only appropriate for calibration
tasks where Bpod-timed pulses and trial recording are needed. Here we just want
firmware-level open/close with host-side sleep for timing.
"""

import logging
import time

from pybpodapi.bpod.hardware.channels import ChannelName, ChannelType

from murineshiftwork.logic.config.models import ActionRequest


class BpodActionDriver:
    """Execute discrete Bpod valve actions via firmware manual_override().

    Supported actions
    -----------------
    valve_pulse  — open valve for duration_s, repeated n_pulses times
                   params: valve_id (int, default 1), duration_s (float, default 0.025),
                           n_pulses (int, default 1), inter_pulse_s (float, default 0.150)
    valve_flush  — rapid many-pulse flush; same params with higher-volume defaults
                   params: valve_id (int, default 1), duration_s (float, default 0.050),
                           n_pulses (int, default 200), inter_pulse_s (float, default 0.100)
    """

    SUPPORTED_ACTIONS = frozenset({"valve_pulse", "valve_flush"})

    def __init__(self, bpod) -> None:
        self._bpod = bpod

    def dispatch(self, request: ActionRequest) -> None:
        if request.action not in self.SUPPORTED_ACTIONS:
            raise ValueError(
                f"Unknown action {request.action!r}. "
                f"Supported: {sorted(self.SUPPORTED_ACTIONS)}"
            )
        getattr(self, f"_{request.action}")(request.params)

    def _valve_pulse(self, params: dict) -> None:
        self._run_valve(
            valve_id=int(params.get("valve_id", 1)),
            duration_s=float(params.get("duration_s", 0.025)),
            n_pulses=int(params.get("n_pulses", 1)),
            inter_pulse_s=float(params.get("inter_pulse_s", 0.150)),
        )

    def _valve_flush(self, params: dict) -> None:
        self._run_valve(
            valve_id=int(params.get("valve_id", 1)),
            duration_s=float(params.get("duration_s", 0.050)),
            n_pulses=int(params.get("n_pulses", 200)),
            inter_pulse_s=float(params.get("inter_pulse_s", 0.100)),
        )

    def _run_valve(
        self,
        valve_id: int,
        duration_s: float,
        n_pulses: int,
        inter_pulse_s: float,
    ) -> None:
        logging.info(
            f"BpodAction: valve {valve_id} | {duration_s:.4f}s | "
            f"{n_pulses} pulse(s) | {inter_pulse_s:.3f}s ITI"
        )
        try:
            for i in range(n_pulses):
                self._bpod.manual_override(
                    ChannelType.OUTPUT, ChannelName.VALVE, valve_id, 1
                )
                time.sleep(duration_s)
                self._bpod.manual_override(
                    ChannelType.OUTPUT, ChannelName.VALVE, valve_id, 0
                )
                if i < n_pulses - 1:
                    time.sleep(inter_pulse_s)
        finally:
            # Ensure valve is closed even if interrupted mid-pulse
            try:
                self._bpod.manual_override(
                    ChannelType.OUTPUT, ChannelName.VALVE, valve_id, 0
                )
            except Exception:
                pass
        logging.info("BpodAction: complete")
