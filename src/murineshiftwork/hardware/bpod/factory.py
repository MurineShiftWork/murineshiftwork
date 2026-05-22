import importlib
import logging
import threading
import time


class BpodFactory:
    """Context-manager wrapper around pybpodapi Bpod with auto 4/8-port detection
    and retry on transient serial errors.

    Root cause of first-connect failures: opening a USB-CDC ttyACM device toggles
    DTR, which resets the Arduino firmware. The firmware takes ~1–2 s to boot;
    pybpodapi's handshake fires immediately and gets garbage bytes back
    (UnicodeDecodeError, wrong-byte BpodErrorException, or empty reads). Sleeping
    retry_delay_s before the next attempt lets the firmware settle.

    Connection happens in open(), not in __init__, so callers can construct
    BpodFactory() before the serial port is accessible and call open() later.

    _write_lock serialises serial writes for future ControllerSession override
    injection during a running state machine.
    """

    _SETTINGS_STANDARD = "murineshiftwork.hardware.bpod.user_settings"
    _SETTINGS_8PORT = "murineshiftwork.hardware.bpod.user_settings_8port"

    def __init__(
        self,
        serial_port="/dev/ttyACM0",
        workspace_path=None,
        session_name=None,
        connect_retries=3,
        retry_delay_s=2.0,
        **kwargs,
    ):
        self.serial_port = serial_port
        self.workspace_path = workspace_path
        self.session_name = session_name
        self.connect_retries = connect_retries
        self.retry_delay_s = retry_delay_s
        self._bpod_kwargs = kwargs

        self._bpod = None
        self._connected = False
        self._exiting = False
        self._write_lock = threading.Lock()
        self._port_config = "unknown"

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
        """Open the Bpod connection, retrying on transient serial errors.

        Sleeps retry_delay_s before each retry so the Arduino firmware has
        time to finish booting after the USB-DTR reset that open() triggers.
        """
        if self._connected or self._exiting:
            return
        retries = max_try if max_try is not None else self.connect_retries
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            if attempt > 1:
                logging.warning(
                    "Bpod connect attempt %d/%d on %s "
                    "(sleeping %.1f s for firmware settle)...",
                    attempt,
                    retries,
                    self.serial_port,
                    self.retry_delay_s,
                )
                time.sleep(self.retry_delay_s)
            try:
                self._bpod = self._create_bpod_object()
                self._connected = True
                hw = self._bpod._hardware
                fw = getattr(hw, "firmware_version", "?")
                mt = getattr(hw, "machine_type", None)
                _MACHINE_NAMES = {1: "r0.5", 2: "r0.7", 3: "r2.0", 4: "r2+"}
                machine = _MACHINE_NAMES.get(mt, f"type={mt}")
                logging.info(
                    "Bpod connected on %s | %s | fw %s | %s",
                    self.serial_port,
                    self._port_config,
                    fw,
                    machine,
                )
                return
            except Exception as exc:
                self._close_partial(self._bpod)
                self._bpod = None
                last_exc = exc
                logging.warning(
                    "Bpod connect attempt %d/%d failed: %s: %s",
                    attempt,
                    retries,
                    type(exc).__name__,
                    exc,
                )
        raise RuntimeError(
            f"Failed to connect to Bpod at {self.serial_port!r} after {retries} attempts. "
            f"Last error: {type(last_exc).__name__}: {last_exc}. "
            "Power-cycle the Bpod and try again."
        ) from last_exc

    def close_safely(self):
        """Stop any running trial and close the connection."""
        self._exiting = True
        if self._connected and self._bpod is not None:
            try:
                self._bpod.stop_trial()
                self._bpod.close()
            except Exception as exc:
                logging.warning("Bpod safe-close error: %s", exc)
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
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._bpod, name)

    # ------------------------------------------------------------------
    # Internal

    def _close_partial(self, bpod) -> None:
        """Close the serial port on a partially-opened pybpodapi Bpod.

        After a failed open(), _arcom may hold an open serial.Serial fd.
        Closing it releases the port so the next retry can open it cleanly.
        """
        if bpod is None:
            return
        try:
            if hasattr(bpod, "_arcom") and bpod._arcom is not None:
                bpod._arcom.close()
        except Exception:
            pass

    def _create_bpod_object(self):
        """Create and connect pybpodapi Bpod, auto-detecting 4 vs 8 port config.

        IndexError from _bpodcom_enable_ports means the port-count setting
        doesn't match the hardware — immediately switch to 8-port settings.
        All other exceptions are propagated to open() which handles retry.
        """
        from confapp import conf
        from pybpodapi import protocol as bpod_protocol

        conf += self._SETTINGS_STANDARD
        importlib.reload(bpod_protocol)

        partial = None
        try:
            partial = bpod_protocol.Bpod(
                serial_port=self.serial_port,
                workspace_path=self.workspace_path,
                session_name=self.session_name,
                **self._bpod_kwargs,
            )
            logging.getLogger("pybpodapi").setLevel(logging.WARNING)
            self._port_config = "4-port"
            return partial
        except IndexError:
            self._close_partial(partial)
            logging.info(
                "4-port config mismatch (IndexError) — retrying with 8-port settings"
            )

        conf += self._SETTINGS_8PORT
        importlib.reload(bpod_protocol)

        bpod = bpod_protocol.Bpod(
            serial_port=self.serial_port,
            workspace_path=self.workspace_path,
            session_name=self.session_name,
            **self._bpod_kwargs,
        )
        logging.getLogger("pybpodapi").setLevel(logging.WARNING)
        self._port_config = "8-port"
        return bpod
