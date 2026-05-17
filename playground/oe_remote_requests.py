if __name__ == "__main__":
    from datetime import datetime
    from pathlib import Path

    import requests

    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    subject = "_test_subject"
    parent_dir = (Path("/home/lbr/data") / subject).as_posix()

    record_options = {
        "parent_directory": parent_dir,
        "base_text": f"{subject}__{dt}__ephys_intan",
        "prepend_text": "",
        "append_text": "",
        # "record_nodes": [
        #     {
        #         "node_id": 0,
        #         "parent_directory": parent_dir,
        #         "record_engine": "BINARY",
        #         "experiment_number": 1,
        #         "recording_number": 1,
        #         "is_synchronized": True,
        #     }
        # ],
    }

    requests.put(
        url="http://192.168.100.19:37497/api/recording", json=record_options
    )
    requests.put(
        url="http://192.168.100.19:37497/api/recording/103",
        json=record_options,
    )

    requests.put(
        url="http://192.168.100.19:37497/api/status", json={"mode": "IDLE"}
    )

    requests.put(
        url="http://192.168.100.19:37497/api/status", json={"mode": "ACQUIRE"}
    )

    requests.put(
        url="http://192.168.100.19:37497/api/status", json={"mode": "RECORD"}
    )
    requests.put(
        url="http://192.168.100.19:37497/api/status", json={"mode": "IDLE"}
    )
    print(" ")
