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
    if isinstance(sequence, str):
        sequence = [*sequence]

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
            exit_state = "inter_trial_interval"
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
        state_name="inter_trial_interval",
        state_timer=inter_trial_interval,
        state_change_conditions={"Tup": "exit"},
        output_actions=[(output_chanel_pulse, 0)],
    )

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
