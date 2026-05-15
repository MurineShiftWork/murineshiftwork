SETTINGS_PRIORITY = -1

# Required to prevent IndexError when connecting to an 8-port Bpod.
# pybpodapi iterates over wired_inputports_indexes to set inputs_enabled;
# without this list the loop goes out of range on 8-port hardware.
# See: https://github.com/pybpod/pybpod/issues/95
BPOD_WIRED_PORTS_ENABLED = [True, True, True, True, True, True, True, True]
