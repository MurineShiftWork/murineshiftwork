from pybpodapi.protocol import Bpod, StateMachine

if __name__ == "__main__":
    my_bpod = Bpod(serial_port="/dev/ttyACM0")

    sma = StateMachine(my_bpod)

    sma.add_state(
        state_name="Port1Active1",  # Add a state
        state_timer=0,
        state_change_conditions={Bpod.Events.Port1In: "Port2Active1"},
        output_actions=[(Bpod.OutputChannels.PWM1, 255)],
    )

    sma.add_state(
        state_name="Port2Active1",
        state_timer=0,
        state_change_conditions={Bpod.Events.Port2In: "Port1Active2"},
        output_actions=[(Bpod.OutputChannels.PWM2, 255)],
    )

    sma.add_state(
        state_name="Port1Active2",
        state_timer=0,
        state_change_conditions={Bpod.Events.Port1In: "Port2Active2"},
        output_actions=[(Bpod.OutputChannels.PWM1, 255)],
    )

    sma.add_state(
        state_name="Port2Active2",
        state_timer=0,
        state_change_conditions={Bpod.Events.Port2In: "exit"},
        output_actions=[(Bpod.OutputChannels.PWM2, 255)],
    )

    my_bpod.send_state_machine(sma)

    exit_code = my_bpod.run_state_machine(sma)

    print(exit_code)
    print("Current trial info: {0}".format(my_bpod.session.current_trial))

    my_bpod.close()
