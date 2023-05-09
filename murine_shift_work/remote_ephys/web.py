import time
from pathlib import Path

import requests


class RemoteControlOE:
    ip = None
    port = None
    settings = {}

    append_text = ""
    base_text = "_test_subject_session"
    prepend_text = ""
    parent_directory = "_test_subject_path"
    default_record_engine = "BINARY"

    _mode = "IDLE"

    def __init__(self, ip: str = None, port: int = 37497, **kwargs):
        super().__init__()
        self.ip = str(ip)
        self.port = int(port)
        self.status()
        self._get_presets()

    @property
    def baseurl(self):
        return f"http://{self.ip}:{self.port}/api"

    def _set_status(self, cmd: str = None):
        r = requests.put(f"{self.baseurl}/status", json={"mode": cmd})
        return self.status()

    def _get_status(self):
        r = requests.get(f"{self.baseurl}/status")
        rjson = r.json()
        self._mode = rjson.get("mode")
        return self._mode

    def preview(self):
        return self._set_status(cmd="ACQUIRE")

    def _record_nodes_are_synchronized(self):
        settings = self._get_presets()
        for node in settings.get("record_nodes", []):
            if not node.get("is_synchronized", False):
                return False

        return True

    def record(self, check_interval: float = 0.5):
        self.stop()
        self.preview()
        while not self._record_nodes_are_synchronized():
            print(round(time.time(), 3), "Waiting for synch...")
            time.sleep(check_interval)
        return self._set_status(cmd="RECORD")

    def stop(self):
        return self._set_status(cmd="IDLE")

    def status(self):
        return self._get_status()

    def _get_presets(self):
        r = requests.get(f"{self.baseurl}/recording")
        rjson = r.json()

        if r.ok:
            self.settings = rjson

        return rjson

    def _patch_presets(self):
        settings = self.settings
        settings["append_text"] = self.append_text
        settings["base_text"] = self.base_text
        settings["parent_directory"] = self.parent_directory
        settings["default_record_engine"] = self.default_record_engine
        return settings

    def _set_presets(self, node: int = None, settings: dict = None):
        settings = settings or self._patch_presets()
        node_str = f"/{node}" if node is not None else ""

        r = requests.put(f"{self.baseurl}/recording{node_str}", json=settings)
        return self._get_presets()

    def transmit_settings(self, settings: dict = None):
        self.stop()

        self._set_presets(node=None, settings=settings)

        record_nodes = self.settings.get("record_nodes")
        for node in record_nodes:
            self._set_presets(node=node["node_id"], settings=settings)
