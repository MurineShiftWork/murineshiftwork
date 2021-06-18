import logging
from pathlib import Path
from pybpodapi.bpod import Bpod

from murine_shift_work.tools.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)
from murine_shift_work.tools.paths import make_session_paths

test_sequence = "LLssLLss"

session_paths = make_session_paths(protocol=Path(__file__).parent.name)
bpod = Bpod(
    workspace_path=session_paths["session_data_folder"],
    session_name=session_paths["session_basename"],
)

for bnc_channel in [1, 2]:
    logging.info(
        f"Testing BNC outputs with TTL sequence {test_sequence} on BNC channel {bnc_channel}"
    )
    sma = make_protocol_identifier_ttl_sequence(
        bpod=bpod,
        sequence=test_sequence,
        output_chanel_pulse=eval(f"Bpod.OutputChannels.BNC{bnc_channel}"),
    )

    bpod.send_state_machine(sma)  # Send state machine description to Bpod device

    if not bpod.run_state_machine(sma):
        print("nothing returned")

bpod.close()


if __name__ == "__main__":
    print("main")
