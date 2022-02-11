import logging

import numpy as np
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine


def _compile_pulse(
    sma=None,
    pulse_index=None,
    pulse_duration=None,
    output_chanel_pulse=None,
    inter_pulse_duration=None,
    exit_state=None,
):
    sma.add_state(
        state_name=f"pulse_{pulse_index}_on",
        state_timer=pulse_duration,
        state_change_conditions={"Tup": f"pulse_{pulse_index}_off"},
        output_actions=[(output_chanel_pulse, 1)],
    )

    sma.add_state(
        state_name=f"pulse_{pulse_index}_off",
        state_timer=inter_pulse_duration,
        state_change_conditions={"Tup": exit_state},
        output_actions=[(output_chanel_pulse, 0)],
    )
    return sma


def _add_protocol_ttl(
    sma=None,
    sequence=None,
    pulse_duration=0.005,
    inter_pulse_duration_long=0.500,
    iti=None,
    output_chanel_pulse=Bpod.OutputChannels.BNC2,
    starting_pulse_index=0,
    exit_state="exit",
):
    assert (
        isinstance(sequence, str)
        or isinstance(sequence, list)
        or isinstance(sequence, tuple)
    )
    iti_state_name = "pulse_post_protocol_identifier"

    if isinstance(sequence, str):
        sequence = [*sequence]

    if iti is None:
        iti = round(2 * inter_pulse_duration_long, 3)

    logging.info(
        f"Sending protocol TTL identifier: {sequence} on output channel {output_chanel_pulse}"
    )

    for pulse_index, pulse_type in enumerate(sequence):
        pulse_type = pulse_type.upper()
        if pulse_type.startswith("L"):
            ipi = round(inter_pulse_duration_long, 3)
        elif pulse_type.startswith("S"):
            ipi = round(inter_pulse_duration_long / 2, 3)
        else:
            raise ValueError(
                f"Pulse type has to be either 'LONG' or 'SHORT' as a string, but is {pulse_type}"
            )

        sma = _compile_pulse(
            sma=sma,
            pulse_index=starting_pulse_index + pulse_index + 1,
            pulse_duration=pulse_duration,
            output_chanel_pulse=output_chanel_pulse,
            inter_pulse_duration=ipi,
            exit_state=iti_state_name
            if pulse_index == len(sequence) - 1
            else f"pulse_{starting_pulse_index+pulse_index+2}_on",
        )

    sma.add_state(
        state_name=iti_state_name,
        state_timer=iti,
        state_change_conditions={"Tup": exit_state},
        output_actions=[(output_chanel_pulse, 0)],
    )

    return sma


def _add_random_identifier(
    sma=None,
    bits=32,
    pulse_duration=0.02,
    inter_pulse_interval_long=0.02,
    iti=None,
    output_chanel_pulse=Bpod.OutputChannels.BNC2,
    starting_pulse_index=0,  # FIXME: upstream
    exit_state="exit",
):
    barcode = f"{np.random.randint(low=0, high=2**bits):b}"
    iti_state_name = "pulse_post_random_identifier"
    if iti is None:
        iti = round(2 * inter_pulse_interval_long, 3)

    logging.info(
        f"Sending random TTL identifier: {barcode} on output channel {output_chanel_pulse}"
    )

    for bit_index, bit in enumerate(barcode):
        if int(bit):
            ipi = inter_pulse_interval_long
        else:
            ipi = round(inter_pulse_interval_long / 2, 3)

        sma = _compile_pulse(
            sma=sma,
            pulse_index=starting_pulse_index + bit_index + 1,
            pulse_duration=pulse_duration,
            output_chanel_pulse=output_chanel_pulse,
            inter_pulse_duration=ipi,
            exit_state=iti_state_name
            if bit_index == len(barcode) - 1
            else f"pulse_{starting_pulse_index+bit_index+2}_on",
        )

    sma.add_state(
        state_name=iti_state_name,
        state_timer=iti,
        state_change_conditions={"Tup": exit_state},
        output_actions=[(output_chanel_pulse, 0)],
    )

    return sma


def make_ttl_identifier_sequences(
    bpod=None,
    sequence=None,
    pulse_duration=0.005,
    inter_pulse_duration_long=0.500,
    iti=None,
    output_chanel_pulse=Bpod.OutputChannels.BNC2,
):
    sma = StateMachine(bpod)

    starting_pulse_index = len(sequence)
    sma = _add_protocol_ttl(
        sma=sma,
        sequence=sequence,
        pulse_duration=pulse_duration,
        inter_pulse_duration_long=inter_pulse_duration_long,
        iti=iti,
        output_chanel_pulse=output_chanel_pulse,
        starting_pulse_index=0,
        exit_state=f"pulse_{starting_pulse_index}_on",
    )

    sma = _add_random_identifier(
        sma=sma,
        bits=32,
        pulse_duration=pulse_duration,
        inter_pulse_interval_long=0.1,
        iti=iti,
        output_chanel_pulse=output_chanel_pulse,
        starting_pulse_index=starting_pulse_index,
        exit_state="exit",
    )
    return sma


def make_protocol_identifier_ttl_sequence(
    bpod=None,
    sequence=None,
    pulse_duration=0.005,
    inter_pulse_duration_long=0.500,
    inter_trial_interval=None,
    output_chanel_pulse=Bpod.OutputChannels.BNC2,
):
    if isinstance(sequence, str):
        sequence = [*sequence]

    if inter_trial_interval is None:
        inter_trial_interval = round(2 * inter_pulse_duration_long, 3)

    logging.info(
        f"Sending protocol TTL identifier: {sequence} on output channel {output_chanel_pulse}"
    )

    # FIXME: add random sequence to identify the specific run for repeat protocol: f"{np.random.randint(0, 511):09b}"

    sma = StateMachine(bpod)

    for pidx, pulse in enumerate(sequence):
        # make __read_next_frame pulse
        if pulse.upper().startswith("L"):
            inter_pulse_duration = round(inter_pulse_duration_long, 3)
        elif pulse.upper().startswith("S"):
            inter_pulse_duration = round(inter_pulse_duration_long / 2, 3)
        else:
            raise ValueError(
                f"Pulse type has to be either 'LONG' or 'SHORT' as a string, but is {pulse}"
            )

        # if is last pulse, add transition to inter-trial interval, otherwise to __read_next_frame pulse
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
        raise ValueError(
            f"bnc_channel variable can only be list, tuple or str, but is {bnc_channel}"
        )

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
