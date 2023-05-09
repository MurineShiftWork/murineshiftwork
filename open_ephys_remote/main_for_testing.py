import json
import logging
import time
from datetime import datetime
from pathlib import Path
from pprint import pprint

from open_ephys_remote.controller import OERemoteController

if __name__ == "__main__":

    def _get_date_str():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    ip = "192.168.100.240"
    dt = _get_date_str()
    subject = "s079_antidromicdrug_m1098899_R"
    # subject = "_test_subject2"
    main_session_folder = "__".join([subject, dt, "ephys_multi_behavior"])
    session_name = "__".join([subject, dt, "ephys_pxi"])

    local_path = Path("/mnt/fastdata/data")

    local_path_full = (
        Path(local_path) / subject / main_session_folder / session_name
    )
    local_path_full.mkdir(parents=True, exist_ok=True)

    metadata_file = local_path_full / f"{session_name}.settings.ephys.json"

    local_path_full = str(local_path_full)
    metadata_file = str(metadata_file)

    settings = {
        "append_text": "",
        "base_text": f"{main_session_folder}",  # session_name,
        "prepend_text": "",
        "parent_directory": rf"E:\\\\OE_DATA\\\\LBR\\\\{subject}",  # main_session_folder
    }

    var = {
        "acquisition_name": subject,
        "acquisition_task_name": "ephys_multi_behaviour",
        "create_new_dir": True,
        "datetime": dt,
        "full_acquisition_name": main_session_folder,
        "full_session_name": session_name,
        "input_args": [],
        "input_kwargs": {
            "debug": False,
            "metadata_list": [],
            "preview": False,
            "record": True,
            "status": False,
        },
        "is_child_session_to": "",
        "local_path": "/mnt/fastdata/data/",
        "local_path_full": "/mnt/fastdata/data/s079_antidromicdrug_m1098899_R/s079_antidromicdrug_m1098899_R__20230323_114524__ephys_multi_behaviour/s079_antidromicdrug_m1098899_R__20230323_114524__ephys_pxi",
        "metadata_file": "/mnt/fastdata/data/s079_antidromicdrug_m1098899_R/s079_antidromicdrug_m1098899_R__20230323_114524__ephys_multi_behaviour/s079_antidromicdrug_m1098899_R__20230323_114524__ephys_pxi/s079_antidromicdrug_m1098899_R__20230323_114524__ephys_pxi.settings.ephys.json",
        "remote_ip": ip,
        "remote_path": settings["parent_directory"],
        "remote_port": 5558,
        "remote_tcp_address": f"tcp://{ip}:5558",
        "session_name": "ephys_pxi",
        "subject": subject,
        "timeout": 1,
    }

    with open(metadata_file, "w") as f:
        out_json = json.dumps(var, indent=4, sort_keys=True)
        f.write(out_json)
        logging.debug(f"Metadata written to: {metadata_file}")
        logging.info(out_json)

    # # # #
    rm = OERemoteController(ip=ip)
    print(f"-> STATUS: {rm.status}")

    settings = {
        "append_text": "",
        "base_text": f"{session_name}",
        "prepend_text": "",
        "parent_directory": f"E:\\\\OE_DATA\\\\LBR\\\\{subject}\\\\{main_session_folder}",  # main_session_folder
    }
    rm.set_settings(node=None, settings=settings)
    rm.set_all_record_nodes(settings=settings)

    rm.preview()
    # time.sleep(2)
    rm.record()

    pprint(rm.settings)

    print((Path(main_session_folder) / session_name).as_posix())

    from open_ephys.control.http_server import OpenEphysHTTPServer

    o = OpenEphysHTTPServer(address=ip)
    o.set_parent_dir(settings.get("parent_directory"))
    # o.set_file_path(settings.get("parent_directory"))
    # o.set_record_path(105, settings.get("parent_directory"))
    o.set_base_text(settings.get("base_text"))
    o.set_append_text("")
    o.set_prepend_text("")
    o.set_start_new_dir()
    o.record(5)

    print(" ")
