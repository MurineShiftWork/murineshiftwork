import json
import time

import requests


class OEController:
    """HTTP controller for Open Ephys GUI v1+ (port 37497 by default).

    Request format mirrors open_ephys.control.OpenEphysHTTPServer:
    uses data=json.dumps(payload) rather than json=payload, which is
    what the OE HTTP server expects.
    """

    MODE_IDLE = "IDLE"
    MODE_ACQUIRE = "ACQUIRE"
    MODE_RECORD = "RECORD"

    def __init__(self, ip: str = "localhost", port: int = 37497):
        self.ip = ip
        self.port = port

    @property
    def _base(self) -> str:
        return f"http://{self.ip}:{self.port}/api"

    def _put(self, endpoint: str, payload: dict) -> dict:
        r = requests.put(
            self._base + endpoint,
            data=json.dumps(payload),
        )
        r.raise_for_status()
        return r.json()

    def _get(self, endpoint: str) -> dict:
        r = requests.get(self._base + endpoint)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Mode control
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        return self._get("/status")["mode"]

    def preview(self) -> None:
        self._put("/status", {"mode": self.MODE_ACQUIRE})

    def stop(self) -> None:
        self._put("/status", {"mode": self.MODE_IDLE})

    # ------------------------------------------------------------------
    # Recording configuration
    # ------------------------------------------------------------------

    @property
    def recording(self) -> dict:
        return self._get("/recording")

    def configure_recording(self, parent_directory: str, base_text: str) -> None:
        """Configure recording path on all Record Nodes.

        parent_directory is set per Record Node (the only call that affects
        nodes already in the signal chain). base_text carries the full
        subdirectory hierarchy as a forward-slash path and is set globally.
        OE creates all levels in base_text when recording starts.
        """
        # base_text and text fields are global settings
        self._put("/recording", {
            "base_text": base_text,
            "prepend_text": "",
            "append_text": "",
        })

        # parent_directory must be set per node for existing Record Nodes
        for node in self.recording.get("record_nodes", []):
            self._put(
                f"/recording/{node['node_id']}",
                {"parent_directory": parent_directory},
            )

    # ------------------------------------------------------------------
    # Record with sync wait
    # ------------------------------------------------------------------

    def _nodes_synchronized(self) -> bool:
        for node in self.recording.get("record_nodes", []):
            if not node.get("is_synchronized", False):
                return False
        return True

    def record(self, poll_interval: float = 0.5) -> None:
        while not self._nodes_synchronized():
            print(f"[{time.strftime('%H:%M:%S')}] Waiting for streams to synchronize...")
            time.sleep(poll_interval)
        self._put("/status", {"mode": self.MODE_RECORD})
