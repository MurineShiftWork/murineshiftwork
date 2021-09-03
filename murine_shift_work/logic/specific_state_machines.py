import logging

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine


def make_protocol_identifier_ttl_sequence(
    bpod=None,
    sequence=None,
    pulse_duration=0.050,
    inter_pulse_duration_long=0.500,
    inter_trial_interval=4,
    output_chanel_pulse=Bpod.OutputChannels.BNC2,
):
    print(
        f"Generating protocol identifier TTL sequence '{sequence}' on output channel {output_chanel_pulse}"
    )
    if isinstance(sequence, str):
        sequence = [*sequence]

    logging.info(f"Sending protocol TTL identifier: {sequence}")

    sma = StateMachine(bpod)

    for pidx, pulse in enumerate(sequence):
        # make next pulse
        if pulse.upper().startswith("L"):
            inter_pulse_duration = round(inter_pulse_duration_long, 3)
        elif pulse.upper().startswith("S"):
            inter_pulse_duration = round(inter_pulse_duration_long / 2, 3)
        else:
            raise ValueError(
                f"Pulse type has to be either 'LONG' or 'SHORT' as a string, but is {pulse}"
            )

        # if is last pulse, add transition to inter-trial interval, otherwise to next pulse
        if pidx == len(sequence) - 1:
            exit_state = "pulse_trial_post_interval"
        else:
            exit_state = f"pulse_{pidx+1}_on"

        sma.add_state(
            state_name=f"pulse_{pidx}_on",
            state_timer=pulse_duration,
            state_change_conditions={"Tup": f"pulse_{pidx}_off"},
            output_actions=[(output_chanel_pulse, 1)],
        )

        sma.add_state(
            state_name=f"pulse_{pidx}_off",
            state_timer=inter_pulse_duration,
            state_change_conditions={"Tup": exit_state},
            output_actions=[(output_chanel_pulse, 0)],
        )

    # Inter-trial interval
    sma.add_state(
        state_name="pulse_trial_post_interval",
        state_timer=inter_trial_interval,
        state_change_conditions={"Tup": "exit"},
        output_actions=[(output_chanel_pulse, 0)],
    )

    return sma


def add_trial_onset_ttl(
    sma=None,
    state_name_tuple=("ttl_on", "ttl_off"),
    ttl_pulse_duration=None,
    bnc_channel=Bpod.OutputChannels.BNC2,
    next_state=None,
):
    if not isinstance(bnc_channel, list) or not isinstance(bnc_channel, tuple):
        bnc_channel = [bnc_channel]

    if not isinstance(bnc_channel[0], str):
        raise ValueError("bnc_channel variable can only be list, tuple or str.")

    logging.debug(f"Sending trial onset TTL: {ttl_pulse_duration}s on {bnc_channel}")

    sma.add_state(
        state_name=state_name_tuple[0],
        state_timer=ttl_pulse_duration,
        state_change_conditions={Bpod.Events.Tup: state_name_tuple[1]},
        output_actions=[(ch, 1) for ch in bnc_channel],
    )
    sma.add_state(
        state_name=state_name_tuple[1],
        state_timer=0,
        state_change_conditions={Bpod.Events.Tup: next_state},
        output_actions=[(ch, 0) for ch in bnc_channel],
    )
    return sma


def make_sma_for_drop_of_water(
    bpod=None,
    valve_opening_time=0,
    valve_ids=1,
    inter_drop_interval=0.1,
):
    """
    valve_ids can be list or int
    inter_drop_interval: might keep valves from overheating
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
