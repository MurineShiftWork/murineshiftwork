from ttl_barcoder.core.barcode_ttl import BarcodeTTL
from ttl_barcoder.core.config import BarcodeConfig
from ttl_barcoder.hardware.bpod.sender import (
    BARCODE_FIRST_STATE_NAME,
    inject_barcode_states,
)

__all__ = [
    "BARCODE_FIRST_STATE_NAME",
    "inject_barcode_states",
    "prepare_barcode",
    "barcode_config_from_settings",
]


def prepare_barcode(barcoder: BarcodeTTL) -> tuple[int, float, list]:
    """Generate barcode, capture wall time, return timing sequence.

    Delegates to BarcodeTTL.prepare(). Wall time is captured before generate()
    so it is consistent with the timestamp encoded in the barcode.

    Returns (barcode_value, wall_time, timing_sequence).
    """
    return barcoder.prepare()


def barcode_config_from_settings(settings: dict) -> BarcodeConfig:
    """Build BarcodeConfig from MSW task settings dict, with defaults."""
    return BarcodeConfig(
        barcode_bits=settings.get("barcode_bits", 37),
        bit_duration_ms=settings.get("barcode_bit_duration_ms", 35.0),
        init_duration_ms=settings.get("barcode_init_duration_ms", 10.0),
        tolerance=settings.get("barcode_tolerance", 0.25),
    )
