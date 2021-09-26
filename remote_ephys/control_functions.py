import json
import logging
import os.path
from datetime import datetime
from pathlib import Path

import zmq

# TODO
#  CLI operations
#  --status -> check is_previewing, is_recording, get_recording_path
#  --preview -> toggle acquisition on/off
#  --record -> toggle recording on/off  ->> start new recording every time
#
# TODO
#   add "rich" logging or use function from MSW
#
# TODO
#  mirror folder structure on local machine : BOOLEAN
#  -->> make acquisition folder and write paths as json metadata
#
# Path structure
# MSW: /base/subject/[subject__dt__task]
# Ephys: /base/subject/[subject__dt__EPHYS]/ session data is in here
#   MSW child sessions:
#        /base/subject/[subject__dt__EPHYS]/[msw session folders]/[msw files + rcc files if video recorded]


class RemoteEphysControl:
    address = "127.0.0.1"
    port = 5557
    network_address = None
    timeout = 1
    acquisition_name = "_test_acquisition"
    acquisition_task = "ephys_multibehaviour"
    remote_acquisition_path = ""
    local_data_path = os.path.expanduser("~/data")
    create_new_dir = True

    datetime = None
    full_acquisition_name = None

    def __init__(
        self,
        address=None,
        port=None,
        timeout=1,
        acquisition_name=None,
        acquisition_task=None,
        remote_acquisition_path=None,
        local_data_path=None,
        create_new_dir=True,
    ):
        """
        https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html
        https://github.com/open-ephys/plugin-GUI/blob/master/Resources/Python/record_control_example_client.py
        """
        super(RemoteEphysControl, self).__init__()

        self.address = address or self.address
        self.port = port or self.port
        self.network_address = f"tcp://{self.address}:{self.port}"
        self.timeout = timeout or self.timeout
        self.acquisition_name = acquisition_name or self.acquisition_name
        self.acquisition_task = acquisition_task or self.acquisition_task
        self.remote_acquisition_path = (
            remote_acquisition_path or self.remote_acquisition_path
        )
        self.local_data_path = local_data_path or self.local_data_path
        self.create_new_dir = create_new_dir or self.create_new_dir

    def _make_full_acquisition_name(self):
        self.datetime = self._get_date_str()
        self.full_acquisition_name = "__".join(
            [self.acquisition_name, self.datetime, self.acquisition_task]
        )
        return self.full_acquisition_name

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        d = {
            "Full acquisition name": self.full_acquisition_name or "<NOT_YET_DEFINED>",
            "Acquisition path": self.remote_acquisition_path,
            "Network address": self.network_address,
        }
        s = "\n\tRemoteEphysControl:\n\n"
        for k, v in d.items():
            s += f"{k:>30}:{'':>2}{v}\n"
        s += "\n"
        return s

    @staticmethod
    def _get_date_str():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def send_message(self, message=None):
        received = None
        with zmq.Context() as context:
            with context.socket(zmq.REQ) as socket:
                socket.RCVTIMEO = int(self.timeout * 1000)

                logging.debug(f"Connecting on address: {self.network_address}")
                socket.connect(self.network_address)

                logging.debug(f"Sending message: {message}")
                socket.send(str(message).encode())

                received = socket.recv()
                logging.info(f"Received message: {received.decode()}")

        return received

    def is_previewing(self):
        return self.send_message(message="IsAcquiring")

    def is_recording(self):
        return self.send_message(message="IsRecording")

    def get_recording_path(self):
        return self.send_message(message="GetRecordingPath")

    def start_preview(self):
        return self.send_message(message="StartAcquisition")

    def stop_preview(self):
        return self.send_message(message="StopAcquisition")

    def start_recording(self):
        """
        StartRecord
            [CreateNewDir=1]
            [RecDir=recording_directory_path]
            [PrependText=some_text]
            [AppendText=some_text]
        """
        prepend_text = self._make_full_acquisition_name()
        append_text = ""
        message = (
            f"StartRecord "
            f"CreateNewDir={1 if self.create_new_dir else 0} "
            f"RecDir={self.remote_acquisition_path}\\{prepend_text} "
            f"PrependText={prepend_text} "
            f"AppendText={append_text} "
        )

        if self.mirror_remote_paths:
            out_file = (
                Path(self.local_data_path) / prepend_text / f"{prepend_text}.json"
            )
            with open(out_file, "w") as f:
                f.write(json.dumps({}, indent=4, sort_keys=True))
                logging.debug(f"Metadata written to: {out_file}")

        return self.send_message(message=message)

    def stop_recording(self):
        return self.send_message(message="StopRecord")


if __name__ == "__main__":
    e = RemoteEphysControl(remote_acquisition_path="F:\\some_folder\\")

    print(" ")
