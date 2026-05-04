import logging
import time

from ttl_barcoder.core.barcode_ttl import BarcodeTTL
from ttl_barcoder.core.config import BarcodeConfig

# Canonical state name for the first barcode state — used as alignment key in df
BARCODE_FIRST_STATE_NAME = "barcode_start"


def prepare_barcode(barcoder: BarcodeTTL) -> tuple[int, float, list]:
    """Generate barcode, capture wall time, return timing sequence.

    Wall time is captured before generate() so it matches the timestamp
    encoded in the barcode value (for TTLType.timestamp configs).

    Returns:
        (barcode_value, wall_time, timing_sequence)
    """
    wall_time = time.time()
    barcode_value = barcoder.generator.generate(timestamp=wall_time)
    timing_sequence = barcoder.get_sequence(barcode=barcode_value)
    return barcode_value, wall_time, timing_sequence


def inject_barcode_states(
    sma,
    timing_sequence: list[tuple[bool, float]],
    bnc_channel,
    first_state_name: str = BARCODE_FIRST_STATE_NAME,
    last_state_name: str = "exit",
):
    """Inject barcode states into a pybpodapi StateMachine.

    Uses MSW-compatible list-of-tuples output_actions format.
    Each bit in the timing sequence becomes one state, chained via Tup.

    Args:
        sma: pybpodapi StateMachine to modify in-place
        timing_sequence: list of (level: bool, duration_ms: float) from BarcodeTTL.get_sequence()
        bnc_channel: Bpod output channel, e.g. Bpod.OutputChannels.BNC2
        first_state_name: name for the first barcode state — used as alignment key
        last_state_name: state to transition to after barcode completes

    Returns:
        Modified StateMachine
    """
    n = len(timing_sequence)
    for i, (level, duration_ms) in enumerate(timing_sequence):
        state_name = first_state_name if i == 0 else f"{first_state_name}_seg_{i}"
        next_state = last_state_name if i == n - 1 else f"{first_state_name}_seg_{i + 1}"

        sma.add_state(
            state_name=state_name,
            state_timer=duration_ms / 1000.0,
            state_change_conditions={"Tup": next_state},
            output_actions=[(bnc_channel, 1 if level else 0)],
        )

    logging.debug(
        f"Injected {n} barcode states ({first_state_name} → {last_state_name}), "
        f"total {sum(d for _, d in timing_sequence):.0f}ms"
    )
    return sma


def barcode_config_from_settings(settings: dict) -> BarcodeConfig:
    """Build BarcodeConfig from task settings dict, with defaults."""
    return BarcodeConfig(
        barcode_bits=settings.get("barcode_bits", 37),
        bit_duration_ms=settings.get("barcode_bit_duration_ms", 35.0),
        init_duration_ms=settings.get("barcode_init_duration_ms", 10.0),
        tolerance=settings.get("barcode_tolerance", 0.25),
    )
