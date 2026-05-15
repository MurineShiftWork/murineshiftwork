from murineshiftwork.hardware.bpod.factory import BpodFactory
from murineshiftwork.hardware.bpod.ttl import (
    add_trial_onset_ttl,
    make_ttl_identifier_sequences,
)
from murineshiftwork.hardware.bpod.water import make_sma_for_drop_of_water


def patch_user_settings():
    """Patch MSW pybpod user settings into the confapp configuration."""
    from confapp import conf
    conf += "murineshiftwork.hardware.bpod.user_settings"
