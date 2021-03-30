from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine


def make_protocol_identifier_ttl_sequence(bpod=None, sequence=None):
    # FIXME: add state machine for TTL sequence
    sma = StateMachine(bpod=bpod)
    # sma.add_state(
    #     state_name="drop",
    #     state_timer=valve_on_time,
    #     state_change_conditions={"Tup": "exit"},
    #     output_actions=[(Bpod.OutputChannels.Valve, valve_code)],
    # )
    return sma


def make_sma_for_drop_of_water(bpod=None, valve_on_time=0, valve_code=1):
    sma = StateMachine(bpod=bpod)
    sma.add_state(
        state_name="drop",
        state_timer=valve_on_time,
        state_change_conditions={"Tup": "exit"},
        output_actions=[(Bpod.OutputChannels.Valve, valve_code)],
    )
    return sma
