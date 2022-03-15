import json
import logging
import os.path
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import zmq

# Path structure
# MSW: /base/subject/[subject__dt__task]
# Ephys: /base/subject/[subject__dt__EPHYS]/ session data is in here
#   MSW child sessions:
#        /base/subject/[subject__dt__EPHYS]/[msw session folders]/[msw files + rcc files if video recorded]


class RemoteOpenEphysController:
    remote_ip = "127.0.0.1"
    remote_port = 5558
    remote_tcp_address = None
    timeout = 1
    acquisition_name = "_test_acquisition"
    acquisition_task_name = "ephys_multi_behaviour"
    session_name = ""
    remote_path = ""
    local_path = os.path.expanduser("~/data")
    create_new_dir = True

    datetime = None
    full_acquisition_name = ""
    full_session_name = ""

    local_path_full = ""
    metadata_file = ""
    subject = ""

    default_delay = 0.25

    input_args = []
    input_kwargs = {}

    def __init__(
        self,
        remote_ip=None,
        remote_port=None,
        timeout=1,
        acquisition_name=None,
        acquisition_task=None,
        session_name=None,
        remote_path=None,
        local_path=None,
        create_new_dir=True,
        *args,
        **kwargs,
    ):
        """
        https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html
        https://github.com/open-ephys/plugin-GUI/blob/master/Resources/Python/record_control_example_client.py
        """
        super(RemoteOpenEphysController, self).__init__()

        self.remote_ip = remote_ip or self.remote_ip
        self.remote_port = remote_port or self.remote_port
        self.remote_tcp_address = f"tcp://{self.remote_ip}:{self.remote_port}"
        self.timeout = timeout or self.timeout
        self.acquisition_name = acquisition_name or self.acquisition_name
        self.acquisition_task_name = acquisition_task or self.acquisition_task_name
        self.session_name = session_name or self.session_name
        self.remote_path = str(remote_path).strip("\\") or self.remote_path
        self.local_path = local_path or self.local_path
        self.create_new_dir = create_new_dir or self.create_new_dir

        self.input_args = args
        self.input_kwargs = kwargs

    def _make_full_acquisition_and_session_names(self):
        self.datetime = self._get_date_str()
        self.full_acquisition_name = "__".join(
            [self.acquisition_name, self.datetime, self.acquisition_task_name]
        )
        if not self.session_name:
            self.full_session_name = self.full_acquisition_name
        else:
            self.full_session_name = "__".join(
                [self.acquisition_name, self.datetime, self.session_name]
            )

        return self.full_acquisition_name, self.full_session_name

    def __str__(self):
        d = {
            "Full acquisition name": self.full_acquisition_name or "<NOT_YET_DEFINED>",
            "Full session name": self.session_name or "<NOT_YET_DEFINED>",
            "Acquisition path": self.remote_path,
            "Network address": self.remote_tcp_address,
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

    def _persists_metadata(self, acq_name=None, session_name=None):
        if self.local_path is not None:
            self.local_path_full = (
                Path(self.local_path) / self.acquisition_name / acq_name / session_name
            )
            self.local_path_full.mkdir(parents=True, exist_ok=True)

            self.metadata_file = (
                self.local_path_full / f"{session_name}.settings.ephys.json"
            )

            self.local_path_full = str(self.local_path_full)
            self.metadata_file = str(self.metadata_file)
            self.subject = self.acquisition_name
            with open(self.metadata_file, "w") as f:
                out_json = json.dumps(vars(self), indent=4, sort_keys=True)
                f.write(out_json)
                logging.debug(f"Metadata written to: {self.metadata_file}")
                logging.info(out_json)

        return Path(self.metadata_file).exists()

    def send_message(self, message=None, expected_return=None):
        received = None
        with zmq.Context() as context:
            with context.socket(zmq.REQ) as socket:
                socket.RCVTIMEO = int(self.timeout * 1000)

                logging.debug(f"Connecting on address: {self.remote_tcp_address}")
                socket.connect(self.remote_tcp_address)

                logging.debug(f"Sending message: {message}")
                socket.send_string(message)

                received = socket.recv().decode()
                logging.info(f"Received message: {received}")

        if received == expected_return:
            return True
        else:
            return False

    def is_previewing(self):
        return self.send_message(message="IsAcquiring", expected_return="1")

    def is_recording(self):
        return self.send_message(message="IsRecording", expected_return="1")

    def get_recording_path(self):
        return self.send_message(message="GetRecordingPath")

    def start_preview(self):
        return self.send_message(
            message="StartAcquisition", expected_return="StartedAcquisition"
        )

    def stop_preview(self):
        if self.is_recording() is True:
            self.stop_recording()
            time.sleep(self.default_delay)
        return self.send_message(
            message="StopAcquisition", expected_return="StoppedAcquisition"
        )

    @staticmethod
    def _make_start_message_string(
        create_new_dir=True,
        remote_path="",
        acquisition_name="",
        full_acquisition_name="",
        session_name="",
        session_name_appendix="",
        whitespace=" ",
        path_sep="/" if os.path.sep == "/" else "\\",
    ):
        message = (
            f"StartRecord{whitespace}"
            f"CreateNewDir={1 if create_new_dir else 0}{whitespace}"
            f"RecDir={str(remote_path)}{path_sep}{acquisition_name}{path_sep}{full_acquisition_name}{whitespace}"
            f"PrependText={session_name}{whitespace}"
            f"AppendText={session_name_appendix}{whitespace}"
        )
        return message

    def _send_start_record(self, message):
        return self.send_message(message=message, expected_return="StartedRecording")

    def start_recording(self):
        """
        StartRecord
            [CreateNewDir=1]
            [RecDir=recording_directory_path]
            [PrependText=some_text]
            [AppendText=some_text]
        """
        (
            full_acquisition_name,
            full_session_name,
        ) = self._make_full_acquisition_and_session_names()

        message = self._make_start_message_string(
            create_new_dir=self.create_new_dir,
            remote_path=self.remote_path,
            acquisition_name=self.acquisition_name,
            full_acquisition_name=full_acquisition_name,
            session_name=full_session_name,
        )

        self.start_preview()
        time.sleep(self.default_delay)
        is_previewing = self.is_previewing()
        time.sleep(self.default_delay)
        if is_previewing is True:
            logging.info(
                f"Setting up for ephys session:\n\t{full_acquisition_name}/{full_session_name}\n"
            )
            child_session_path = Path(self.acquisition_name) / full_acquisition_name
            logging.info(
                f"Use as child session path:\n\t{child_session_path.as_posix()}\n"
            )
            record_success = self._send_start_record(message)
            persist_success = self._persists_metadata(
                full_acquisition_name, full_session_name
            )
            return record_success and persist_success
        else:
            logging.info(f"Cannot start preview. Replied: {is_previewing}")

    def safeguard_path_by_overwrite(self, path_sep="/" if os.path.sep == "/" else "\\"):
        session_name = f"acquisition-{uuid4()}"
        message = self._make_start_message_string(
            create_new_dir=True,
            remote_path=self.remote_path
            + path_sep
            + "_safeguard_acquisition",  # r"E:\\OE_DATA\\",
            session_name=session_name,
        )

        self.start_preview()
        time.sleep(self.default_delay)
        is_previewing = self.is_previewing()
        time.sleep(self.default_delay)
        if is_previewing is True:
            logging.info(f"Setting up for session:\t {session_name}")
            logging.info(f"Sesion path:\n\t{self.local_path_full}\n")
            self._send_start_record(message)
        else:
            logging.info(f"Cannot start preview. Replied: {is_previewing}")

        self.stop_recording()
        logging.info("Safeguard session set")

    def stop_recording(self):
        return self.send_message(
            message="StopRecord", expected_return="StoppedRecording"
        )
