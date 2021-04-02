import random

from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

my_bpod = Bpod()

nTrials = 5
trialTypes = [1, 2]  # 1 (rewarded left) or 2 (rewarded right)

for i in range(nTrials):  # Main loop
    print("Trial: ", i + 1)

    thisTrialType = random.choice(trialTypes)  # Randomly choose trial type
    if thisTrialType == 1:
        stimulus = Bpod.OutputChannels.PWM1  # set stimulus channel for trial type 1
        leftAction = "Reward"
        rightAction = "Punish"
        rewardValve = 1
    elif thisTrialType == 2:
        stimulus = Bpod.OutputChannels.PWM3  # set stimulus channel for trial type 1
        leftAction = "Punish"
        rightAction = "Reward"
        rewardValve = 3

    sma = StateMachine(my_bpod)

    sma.add_state(
        state_name="WaitForPort2Poke",
        state_timer=1,
        state_change_conditions={Bpod.Events.Port2In: "FlashStimulus"},
        output_actions=[(Bpod.OutputChannels.PWM2, 255)],
    )
    sma.add_state(
        state_name="FlashStimulus",
        state_timer=0.1,
        state_change_conditions={Bpod.Events.Tup: "WaitForResponse"},
        output_actions=[(stimulus, 255)],
    )
    sma.add_state(
        state_name="WaitForResponse",
        state_timer=1,
        state_change_conditions={
            Bpod.Events.Port1In: leftAction,
            Bpod.Events.Port3In: rightAction,
        },
        output_actions=[],
    )
    sma.add_state(
        state_name="Reward",
        state_timer=0.1,
        state_change_conditions={Bpod.Events.Tup: "exit"},
        output_actions=[(Bpod.OutputChannels.Valve, rewardValve)],
    )  # Reward correct choice
    sma.add_state(
        state_name="Punish",
        state_timer=3,
        state_change_conditions={Bpod.Events.Tup: "exit"},
        output_actions=[
            (Bpod.OutputChannels.LED, 1),
            (Bpod.OutputChannels.LED, 2),
            (Bpod.OutputChannels.LED, 3),
        ],
    )  # Signal incorrect choice

    my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device

    print("Waiting for poke. Reward: ", "left" if thisTrialType == 1 else "right")

    my_bpod.run_state_machine(sma)  # Run state machine

    print("Current trial info: {0}".format(my_bpod.session.current_trial))

my_bpod.close()  # Disconnect Bpod

if __name__ == "__main__":
    print("main")
