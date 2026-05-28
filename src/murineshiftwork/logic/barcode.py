from pathlib import Path

from ttl_barcoder.core.barcode_ttl import BarcodeTTL
from ttl_barcoder.core.config import BarcodeConfig
from ttl_barcoder.hardware.bpod.sender import (
    BARCODE_FIRST_STATE_NAME,
    inject_barcode_states,
)

__all__ = [
    "BarcodeTTL",
    "BarcodeConfig",
    "BARCODE_FIRST_STATE_NAME",
    "inject_barcode_states",
    "barcode_config_from_settings",
    "TTL_IDENTIFIER_SEQUENCES",
    "get_ttl_identifier_sequence",
]

# Per-task TTL barcode identifier sequences.
# Not all tasks use this; some define sequences in their own task.settings.
TTL_IDENTIFIER_SEQUENCES = {
    "probabilistic_switching": "sssLss",
    "optotagging": "LsLsss",
    "periodic_trigger": "Lsssss",
    "periodic_trigger_with_video": "LLssss",
    "sleep_homecage": "sLsLss",
    "openfield": "sLssss",
    "tests": "ssssss",
}


def get_ttl_identifier_sequence(file=None):
    key = Path(file).name.replace(".py", "")
    return TTL_IDENTIFIER_SEQUENCES.get(key)


def barcode_config_from_settings(settings: dict) -> BarcodeConfig:
    """Build BarcodeConfig from MSW task settings dict, with defaults."""
    return BarcodeConfig(
        barcode_bits=settings.get("barcode_bits", 37),
        bit_duration_ms=settings.get("barcode_bit_duration_ms", 35.0),
        init_duration_ms=settings.get("barcode_init_duration_ms", 10.0),
        tolerance=settings.get("barcode_tolerance", 0.25),
    )
