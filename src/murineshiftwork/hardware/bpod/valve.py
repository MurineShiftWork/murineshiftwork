from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine


def make_sma_for_valve_pulse(
    bpod=None,
    valve_opening_time=0,
    valve_ids=1,
    inter_drop_interval=0.1,
):
    """
    valve_ids can be list or int
    inter_drop_interval: gap between open and exit states
    """
    if not hasattr(valve_ids, "__iter__"):
        valve_ids = [valve_ids]

    output_actions = []
    for v in valve_ids:
        output_actions.append((Bpod.OutputChannels.Valve, v))

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


# Back-compat alias
make_sma_for_drop_of_water = make_sma_for_valve_pulse
