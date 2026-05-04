import argparse
import json
import logging
import re
import time

import numpy as np
from open_ephys.control import OpenEphysHTTPServer


def test_gui_idle(ip_address=""):
    gui = OpenEphysHTTPServer(ip_address)
    return gui.status() == "IDLE"


def get_probe_info(ip_address=""):
    gui = OpenEphysHTTPServer(ip_address)

    # processor_info = gui.get_processors()
    processor_npx = gui.get_processors("Neuropix-PXI")
    npx_processor_id = processor_npx[0]["id"]

    npx_info = gui.config(npx_processor_id, "NP INFO")
    npx_info_dict = json.loads(npx_info["info"])
    npx_probes = npx_info_dict["probes"]

    return npx_processor_id, npx_probes


# identify probe:
# - npx1.0 -> 960 sites in 3 banks: 0-383, 384-767, 768-959 ->+1-> 1-384, 385-768, 769-960
# - npx2.0 single -> 1280 sites in 4 banks:  0-383, 384-767, 768-1151, 1152-1279 ->+1-> 1-384, 385-768, 769-1152, 1153-1280
# - npx2.0 multi -> 1280*4: pattern for 2.0-single for offset of 0, 1280, 2*1280, 3*1280
NPX1sites = [
    np.arange(1, 385),  # 384 from 1 - 384
    np.arange(385, 2 * 384 + 1),  # 384 from 385 - 768
    np.arange(2 * 384 + 1, 960 + 1),  # rest from 769 - 960
]
NPX2single = [
    np.arange(1, 385),  # 384 from 1 - 384
    np.arange(385, 2 * 384 + 1),  # 384 from 385 - 769
    np.arange(2 * 384 + 1, 3 * 384 + 1),  # 384 from 769 - 1152
    np.arange(3 * 384 + 1, 1280 + 1),  # rest from 1153 - 1280
]
shank_offset_npx2 = 1280
NPX2multi = [
    array + shank_offset_npx2 * factor
    for factor in range(4)
    for array in NPX2single
]

PROBE_TO_SITES_LIST = {
    "Neuropixels 1.0": {"type": "NPX-2.0-single", "site_groups": NPX1sites},
    "Neuropixels 2.0 - Single Shank": {
        "type": "NPX-2.0-single",
        "site_groups": NPX2single,
    },
    "Neuropixels 2.0 - Multishank": {
        "type": "NP-2.0-multi",
        "site_groups": NPX2multi,
    },
}


def record_all_sites(
    ip_address: str = "",
    npx_processor_id: int = None,
    npx_probes: list = None,
    recording_duration: float = 60,
    recording_directory: str = None,
    recording_name: str = None,
):
    # connect
    gui = OpenEphysHTTPServer(ip_address)
    processor_record_node = gui.get_processors("Record Node")[0]

    # rec dir + rec name + datetime of start
    recording_name_full = f"{recording_name}__{time.strftime('%Y%m%d_%H%M%S')}"
    recording_directory_full = f"{recording_directory}\\{recording_name_full}"
    logging.info(f"Recording directory: {recording_directory_full}")

    _ = gui.set_record_path(
        processor_record_node["id"], recording_directory_full
    )

    # for each probe, record segments of 384 sites for recording_duration
    for probe_info in npx_probes:
        # identify probe
        this_probe_sites = PROBE_TO_SITES_LIST[probe_info["type"]]

        for probe_site_list in this_probe_sites["site_groups"]:
            electrode_string = " ".join(probe_site_list.astype("str"))
            command_for_select = f"NP SELECT {probe_info['slot']} {probe_info['port']} {probe_info['dock']} {electrode_string}"

            # should return dict: info = success
            ret = gui.config(npx_processor_id, command_for_select)
            assert ret["info"] == "SUCCESS"

            time.sleep(1)

            # set recording info: recording_name_full, probe: name/serial/slot/port/dock, site range
            prepend_text = (
                f"{recording_name_full}_{probe_info['name']}_{probe_info['serial_number']}"
                f"_slot{probe_info['slot']}_port{probe_info['port']}_dock{probe_info['dock']}"
                f"_ch{probe_site_list[0]}_ch{probe_site_list[-1]}_"
            )
            print(prepend_text)
            gui.set_start_new_dir()
            gui.set_prepend_text(prepend_text)
            gui.set_append_text("")
            gui.record(recording_duration)

            time.sleep(1)


if __name__ == "__main__":
    # TODO: add argparse CLI with ip-address check from test script

    # recording_name = "seq121"
    # IP_ADDRESS = "172.24.243.152"
    # recording_directory = f"D:\\DATA\\probemapping"

    recording_name = "_test_subject"
    IP_ADDRESS = "172.24.242.168"
    recording_directory = "D:\\DATA\\probemapping"

    # recording_name = "xyz"
    # IP_ADDRESS = "172.24.243.127"  # right rig (new)
    # recording_directory = f"D:\\NPX_DATA\\probemapping"

    # recording_name = "xyz"
    # IP_ADDRESS = "192.168.100.25"  # 3rd rig on wheels
    # recording_directory = f"N:\\lbr\\probemapping"

    record_duration = 20  # seconds

    # test if idle
    if not test_gui_idle(ip_address=IP_ADDRESS):
        AssertionError("GUI HAS TO BE IDLE BEFORE BEGINNING TO MAP SITES.")

    # get probe info
    npx_processor_id, npx_probes = get_probe_info(ip_address=IP_ADDRESS)

    # loop through probes and recording sites
    record_all_sites(
        ip_address=IP_ADDRESS,
        npx_processor_id=npx_processor_id,
        npx_probes=npx_probes,
        recording_duration=record_duration,
        recording_directory=recording_directory,
        recording_name=recording_name,
    )

    print("DONE")
