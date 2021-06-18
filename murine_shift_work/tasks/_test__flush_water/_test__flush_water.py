import logging
from pathlib import Path
from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from murine_shift_work.tools.paths import make_session_paths

# Get user input or empty for defaults
# valve_opening_time = input("Valve opening time (seconds, default: 5): ")
# valve_numbers = input("Valve numbers (default: '1 2 3 4'): ")
#
# valve_opening_time = float(valve_opening_time) if valve_opening_time else 5
# valve_numbers = (
#     [nr for nr in valve_numbers.strip().split(" ") if nr]
#     if valve_numbers
#     else [1, 2, 3, 4]
# )
valve_opening_time = 0.1
valve_numbers = [1, 2, 3, 4]

valves_to_open = []
for valve in valve_numbers:
    # FIXME: check that codes 1,2,3,4 work and not requird to use 1,2,4,8
    valves_to_open.append((Bpod.OutputChannels.Valve, valve))


# Flush valves
session_paths = make_session_paths(protocol=Path(__file__).parent.name)
bpod = Bpod(
    workspace_path=session_paths["session_data_folder"],
    session_name=session_paths["session_basename"],
)

logging.info(f"Flushing water for valve(s) {valve_numbers} for {valve_opening_time}s..")

sma = StateMachine(bpod=bpod)
sma.add_state(
    state_name="drop_it_like_its_water",
    state_timer=valve_opening_time,
    state_change_conditions={"Tup": "exit"},
    output_actions=valves_to_open,
)

bpod.send_state_machine(sma)

# Run state machine
if not bpod.run_state_machine(sma):  # Locks until state machine 'exit' is reached
    logging.debug("No data returned")

bpod.close()

if __name__ == "__main__":
    print("main")
