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
    remote_ephys_address = None
    timeout = 1
    acquisition_name = "_test_acquisition"
    task_name = "ephys_multibehaviour"
    remote_acquisition_path = ""
    local_data_path = os.path.expanduser("~/data")
    create_new_dir = True

    datetime = None
    full_acquisition_name = ""

    local_path = ""
    metadata_file = ""

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
        self.remote_ephys_address = f"tcp://{self.address}:{self.port}"
        self.timeout = timeout or self.timeout
        self.acquisition_name = acquisition_name or self.acquisition_name
        self.task_name = acquisition_task or self.task_name
        self.remote_acquisition_path = (
            remote_acquisition_path or self.remote_acquisition_path
        )
        self.local_data_path = local_data_path or self.local_data_path
        self.create_new_dir = create_new_dir or self.create_new_dir

    def _make_full_acquisition_name(self):
        self.datetime = self._get_date_str()
        self.full_acquisition_name = "__".join(
            [self.acquisition_name, self.datetime, self.task_name]
        )
        return self.full_acquisition_name

    def __str__(self):
        d = {
            "Full acquisition name": self.full_acquisition_name or "<NOT_YET_DEFINED>",
            "Acquisition path": self.remote_acquisition_path,
            "Network address": self.remote_ephys_address,
        }
        s = "\n\tRemoteEphysControl:\n\n"
        for k, v in d.items():
            s += f"{k:>30}:{'':>2}{v}\n"
        s += "\n"
        return s

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def _get_date_str():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def send_message(self, message=None):
        received = None
        with zmq.Context() as context:
            with context.socket(zmq.REQ) as socket:
                socket.RCVTIMEO = int(self.timeout * 1000)

                logging.debug(f"Connecting on address: {self.remote_ephys_address}")
                socket.connect(self.remote_ephys_address)

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
        session_name = self._make_full_acquisition_name()
        append_text = ""
        message = (
            f"StartRecord "
            f"CreateNewDir={1 if self.create_new_dir else 0} "
            f"RecDir={self.remote_acquisition_path}\\{self.acquisition_name}\\{session_name} "
            f"PrependText={session_name} "
            f"AppendText={append_text} "
        )

        if self.local_data_path is not None:
            self.local_path = (
                Path(self.local_data_path) / self.acquisition_name / session_name
            )
            self.local_path.mkdir(parents=True, exist_ok=True)

            self.metadata_file = self.local_path / f"{session_name}.json"

            self.local_path = str(self.local_path)
            self.metadata_file = str(self.metadata_file)
            self.subject = self.acquisition_name
            with open(self.metadata_file, "w") as f:
                f.write(json.dumps(vars(self), indent=4, sort_keys=True))
                logging.debug(f"Metadata written to: {self.metadata_file}")

        return self.send_message(message=message)

    def stop_recording(self):
        return self.send_message(message="StopRecord")


if __name__ == "__main__":
    e = RemoteEphysControl(
        remote_acquisition_path="E:\\OE_DATA\\LBR\\",
        acquisition_name="_test_subject",
        local_data_path=os.path.expanduser("~/data"),
    )
    e.start_recording()
    print(" ")
