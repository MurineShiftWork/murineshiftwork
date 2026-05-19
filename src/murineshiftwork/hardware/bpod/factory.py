import importlib
import logging
import threading


class BpodFactory:
    """Context-manager wrapper around pybpodapi Bpod with auto 4/8-port detection.

    Handles the UnicodeDecodeError that occurs randomly on initial connection,
    and auto-detects 4-port vs 8-port hardware by catching the IndexError that
    pybpodapi raises when BPOD_WIRED_PORTS_ENABLED is not configured for the
    actual number of ports.

    Proxies all attribute access to the underlying Bpod object so callers can
    use it as a drop-in replacement for a bare pybpodapi.protocol.Bpod instance.

    _write_lock: threading.Lock
        Serialises serial writes for Phase 2 ControllerSession override injection.
        Not contended in Phase 1 (CLI actions are blocking / single-threaded), but
        is the infrastructure that lets ControllerSession safely inject manual
        overrides (valve open/close at firmware level) during a running state machine.
    """

    _SETTINGS_STANDARD = "murineshiftwork.hardware.bpod.user_settings"
    _SETTINGS_8PORT = "murineshiftwork.hardware.bpod.user_settings_8port"

    def __init__(
        self,
        serial_port="/dev/ttyACM0",
        workspace_path=None,
        session_name=None,
        connect_retries=2,
        **kwargs,
    ):
        self.serial_port = serial_port
        self.workspace_path = workspace_path
        self.session_name = session_name
        self.connect_retries = connect_retries
        self._bpod_kwargs = kwargs

        self._connected = False
        self._exiting = False
        self._write_lock = threading.Lock()
        self._port_config = "unknown"
        self._bpod = self._create_bpod()

    # ------------------------------------------------------------------
    # Context manager

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_safely()

    def __del__(self):
        self.close_safely()

    # ------------------------------------------------------------------
    # Public API

    def open(self, max_try=None):
        """Open the Bpod connection with retry on UnicodeDecodeError."""
        if self._connected or self._exiting:
            return
        retries = max_try or self.connect_retries
        for attempt in range(1, retries + 1):
            try:
                self._bpod.open()
                self._connected = True
                hw = self._bpod._hardware
                fw = getattr(hw, "firmware_version", "?")
                mt = getattr(hw, "machine_type", None)
                _MACHINE_NAMES = {1: "r0.5", 2: "r0.7", 3: "r2.0", 4: "r2+"}
                machine = _MACHINE_NAMES.get(mt, f"type={mt}")
                logging.info(
                    f"Bpod connected on {self.serial_port}"
                    f" | {self._port_config} | fw {fw} | {machine}"
                )
                return
            except UnicodeDecodeError as exc:
                logging.warning(f"Bpod connect attempt {attempt}/{retries}: {exc}")
        raise RuntimeError(
            f"Failed to connect to Bpod at {self.serial_port} after {retries} attempts "
            "(UnicodeDecodeError). Try again — this is a known transient serial issue."
        )

    def close_safely(self):
        """Stop any running trial and close the connection."""
        self._exiting = True
        if self._connected and self._bpod:
            try:
                self._bpod.stop_trial()
                self._bpod.close()
            except Exception as exc:
                logging.warning(f"Bpod safe-close error: {exc}")
            finally:
                self._connected = False

    # ------------------------------------------------------------------
    # Proxy all attribute access to the underlying Bpod object

    @property
    def softcode_handler_function(self):
        return self._bpod.softcode_handler_function

    @softcode_handler_function.setter
    def softcode_handler_function(self, value):
        self._bpod.softcode_handler_function = value

    def __getattr__(self, name):
        return getattr(self._bpod, name)

    # ------------------------------------------------------------------
    # Internal

    def _create_bpod(self):
        """Create pybpodapi Bpod object, auto-detecting 4 vs 8 port hardware."""
        from confapp import conf
        from pybpodapi import protocol as bpod_protocol

        conf += self._SETTINGS_STANDARD
        importlib.reload(bpod_protocol)

        try:
            bpod = bpod_protocol.Bpod(
                serial_port=self.serial_port,
                workspace_path=self.workspace_path,
                session_name=self.session_name,
                **self._bpod_kwargs,
            )
            logging.getLogger("pybpodapi").setLevel(logging.WARNING)
            self._port_config = "4-port"
            return bpod
        except IndexError:
            logging.info(
                "4-port Bpod config failed (IndexError) — retrying with 8-port settings"
            )
        except Exception as exc:
            raise RuntimeError(
                f"Bpod at {self.serial_port!r} failed to connect: {exc}. "
                "Power-cycle the Bpod and try again."
            ) from exc

        conf += self._SETTINGS_8PORT
        importlib.reload(bpod_protocol)

        try:
            bpod = bpod_protocol.Bpod(
                serial_port=self.serial_port,
                workspace_path=self.workspace_path,
                session_name=self.session_name,
                **self._bpod_kwargs,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Bpod at {self.serial_port!r} failed to connect (8-port): {exc}. "
                "Power-cycle the Bpod and try again."
            ) from exc
        logging.getLogger("pybpodapi").setLevel(logging.WARNING)
        self._port_config = "8-port"
        return bpod
