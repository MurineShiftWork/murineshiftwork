import logging

from pybpodapi.bpod import Bpod

from shift_work.tools.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)

test_sequence = "LLssLLss"

bpod = Bpod()

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
