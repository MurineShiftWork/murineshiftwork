import logging

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine


def make_sma_for_drop_of_water(bpod=None, valve_on_time=0, valve_code=1):
    sma = StateMachine(bpod=bpod)
    sma.add_state(
        state_name="drop",
        state_timer=valve_on_time,
        state_change_conditions={"Tup": "exit"},
        output_actions=[(Bpod.OutputChannels.Valve, valve_code)],
    )
    return sma


bpod = Bpod()
valve_on_time = 5  # seconds
valves = [1, 2, 3, 4]
for valve in valves:
    print(f"Flushing water for valve #{valve} for {valve_on_time}s..")
    sma = make_sma_for_drop_of_water(
        bpod=bpod, valve_on_time=valve_on_time, valve_code=valve
    )
    bpod.send_state_machine(sma)

    # Run state machine
    if not bpod.run_state_machine(sma):  # Locks until state machine 'exit' is reached
        logging.debug("No data returned")
        break

bpod.close()

if __name__ == "__main__":
    print("main")
