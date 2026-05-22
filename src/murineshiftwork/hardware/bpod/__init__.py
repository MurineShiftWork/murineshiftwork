from murineshiftwork.hardware.bpod.device import BpodDevice as BpodDevice
from murineshiftwork.hardware.bpod.factory import BpodFactory as BpodFactory
from murineshiftwork.hardware.bpod.override import BpodOverrideAPI as BpodOverrideAPI
from murineshiftwork.hardware.bpod.ttl import (
    add_trial_onset_ttl as add_trial_onset_ttl,
)
from murineshiftwork.hardware.bpod.ttl import (
    make_ttl_identifier_sequences as make_ttl_identifier_sequences,
)
from murineshiftwork.hardware.bpod.valve import (
    make_sma_for_drop_of_water as make_sma_for_drop_of_water,
)
from murineshiftwork.hardware.bpod.valve import (
    make_sma_for_valve_pulse as make_sma_for_valve_pulse,
)


def patch_user_settings():
    """Patch MSW pybpod user settings into the confapp configuration."""
    from confapp import conf

    conf += "murineshiftwork.hardware.bpod.user_settings"
