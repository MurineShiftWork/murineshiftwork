from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine

# pybpodapi encodes state count and exit sentinel as uint8 (max 255).
# 2 states per pulse (drop + iti) → hard ceiling is 127, use 100 for margin.
_MAX_PULSES_PER_SMA = 100


def make_sma_for_valve_pulse(
    bpod=None,
    valve_opening_time=0,
    valve_ids=1,
    inter_drop_interval=0.1,
):
    """Single valve pulse: one drop + iti state machine.

    valve_ids can be list or int.
    inter_drop_interval: gap between valve close and exit.
    """
    if not hasattr(valve_ids, "__iter__"):
        valve_ids = [valve_ids]

    output_actions = [(Bpod.OutputChannels.Valve, v) for v in valve_ids]

    sma = StateMachine(bpod=bpod)
    sma.add_state(
        state_name="drop",
        state_timer=valve_opening_time,
        state_change_conditions={"Tup": "iti"},
        output_actions=output_actions,
    )
    sma.add_state(
        state_name="iti",
        state_timer=inter_drop_interval,
        state_change_conditions={"Tup": "exit"},
        output_actions=[],
    )
    return sma


def make_sma_for_valve_train(
    bpod=None,
    valve_opening_time: float = 0.005,
    valve_ids=1,
    inter_drop_interval: float = 0.1,
    n_pulses: int = 1,
) -> StateMachine:
    """Chain n_pulses drop+iti pairs into a single state machine.

    Capped at _MAX_PULSES_PER_SMA (128) to stay within Bpod's 256-state limit.
    Sending one SMA per batch instead of one per pulse eliminates the
    USB acknowledgment failures that occur at high pulse counts.
    """
    n_pulses = min(max(1, n_pulses), _MAX_PULSES_PER_SMA)
    if not hasattr(valve_ids, "__iter__"):
        valve_ids = [valve_ids]

    output_actions = [(Bpod.OutputChannels.Valve, v) for v in valve_ids]

    sma = StateMachine(bpod=bpod)
    for i in range(n_pulses):
        next_drop = f"drop_{i + 1}" if i < n_pulses - 1 else "exit"
        sma.add_state(
            state_name=f"drop_{i}",
            state_timer=valve_opening_time,
            state_change_conditions={"Tup": f"iti_{i}"},
            output_actions=output_actions,
        )
        sma.add_state(
            state_name=f"iti_{i}",
            state_timer=inter_drop_interval,
            state_change_conditions={"Tup": next_drop},
            output_actions=[],
        )
    return sma


# Back-compat alias
make_sma_for_drop_of_water = make_sma_for_valve_pulse
