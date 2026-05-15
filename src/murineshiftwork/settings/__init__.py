from pathlib import Path

from murineshiftwork import settings

calibration_data_folder = Path(settings.__file__).parent

TTL_IDENTIFIER_SEQUENCES = {  # FIXME: not used by all protocols. some fall back on own task.settings files
    "probabilistic_switching": "sssLss",
    "optotagging": "LsLsss",
    "periodic_trigger": "Lsssss",
    "periodic_trigger_with_video": "LLssss",
    "openfield": "sLssss",
    "homecage_sleep": "sLsLss",
    "tests": "ssssss",
}


def get_ttl_identifier_sequence(file=None):
    key = Path(file).name.replace(".py", "")
    return TTL_IDENTIFIER_SEQUENCES.get(key, None)
