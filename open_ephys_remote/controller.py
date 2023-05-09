import time

import requests


class OERemoteController:
    ip = None
    port = None
    _settings = {}

    _status = "IDLE"
    _status_stop = "IDLE"
    _status_preview = "ACQUIRE"
    _status_record = "RECORD"

    def __init__(self, ip: str = None, port: int = 37497):
        super().__init__()
        self.ip = str(ip)
        self.port = int(port)

        self._get_settings()
        self._get_status()

    @property
    def baseurl(self):
        """Base URL for API."""
        return f"http://{self.ip}:{self.port}/api"

    def _get_status(self):
        response = requests.get(f"{self.baseurl}/status")
        self._status = response.json().get("mode")
        return self._status

    @property
    def status(self):
        return self._get_status()

    @status.setter
    def status(self, new_status: str = None):
        _ = requests.put(f"{self.baseurl}/status", json={"mode": new_status})
        return self._get_status() == new_status

    def preview(self):
        self.status = self._status_preview
        return self.status == self._status_preview

    def _record_nodes_are_synchronized(self):
        """All streams in record nodes need to be synchronized before recording start, otherwise error in GUI."""
        for node in self.settings.get("record_nodes", []):
            if not node.get("is_synchronized", False):
                return False

        return True

    def record(self, check_interval: float = 0.5):
        while not self._record_nodes_are_synchronized():
            print(
                round(time.time(), 3),
                "Waiting for streams to be synchronized...",
            )
            time.sleep(check_interval)

        self.status = self._status_record
        return self.status == self._status_record

    def stop(self):
        self.status = self._status_stop
        return self.status == self._status_stop

    def _get_settings(self):
        request = requests.get(f"{self.baseurl}/recording")
        if request.ok:
            self._settings = request.json()

    @property
    def settings(self):
        r = requests.get(f"{self.baseurl}/recording")
        rjson = r.json()

        if r.ok:
            self._settings = rjson

        return rjson

    def set_settings(self, node: int = None, settings: dict = None):
        node_str = f"/{node}" if node is not None else ""

        _ = requests.put(f"{self.baseurl}/recording{node_str}", json=settings)
        return self.settings

    def set_all_record_nodes(self, settings: dict = None):
        record_nodes = self.settings.get("record_nodes")
        for node in record_nodes:
            self.set_settings(node=node["node_id"], settings=settings)
