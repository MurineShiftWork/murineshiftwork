"""Tests for HardwareManager, DeviceProtocol, and BpodDevice.

All tests run without physical hardware.  BpodFactory.open() is monkeypatched
where needed so pybpodapi serial connections are never attempted.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from murineshiftwork.hardware.manager import DeviceProtocol, HardwareManager

# ---------------------------------------------------------------------------
# Minimal mock device — reused across HardwareManager tests


class MockDevice:
    def __init__(
        self,
        name: str = "mock",
        fail_preflight: bool = False,
        fail_disconnect: bool = False,
    ):
        self.name = name
        self._fail_preflight = fail_preflight
        self._fail_disconnect = fail_disconnect
        self.preflight_called = False
        self.connect_called = False
        self.disconnect_called = False
        self._handle = object()

    def preflight(self) -> None:
        self.preflight_called = True
        if self._fail_preflight:
            raise ValueError(f"preflight failed for {self.name}")

    def connect(self) -> None:
        self.connect_called = True

    def disconnect(self) -> None:
        self.disconnect_called = True
        if self._fail_disconnect:
            raise RuntimeError(f"disconnect failed for {self.name}")

    @property
    def handle(self) -> Any:
        return self._handle


# ---------------------------------------------------------------------------
# DeviceProtocol structural check


class TestDeviceProtocol:
    def test_mock_device_satisfies_protocol(self):
        assert isinstance(MockDevice(), DeviceProtocol)

    def test_object_without_methods_fails_protocol(self):
        assert not isinstance(object(), DeviceProtocol)

    def test_partial_implementation_fails_protocol(self):
        class NoHandle:
            name = "x"

            def preflight(self): ...
            def connect(self): ...
            def disconnect(self): ...

        assert not isinstance(NoHandle(), DeviceProtocol)


# ---------------------------------------------------------------------------
# HardwareManager


class TestHardwareManager:
    def test_open_calls_preflight_and_connect(self):
        dev = MockDevice()
        HardwareManager([dev]).open()
        assert dev.preflight_called
        assert dev.connect_called

    def test_open_returns_handles_dict(self):
        dev = MockDevice(name="alpha")
        handles = HardwareManager([dev]).open()
        assert handles == {"alpha": dev._handle}

    def test_multiple_devices_all_opened(self):
        d1, d2 = MockDevice("a"), MockDevice("b")
        handles = HardwareManager([d1, d2]).open()
        assert d1.connect_called and d2.connect_called
        assert set(handles) == {"a", "b"}

    def test_close_calls_disconnect(self):
        dev = MockDevice()
        mgr = HardwareManager([dev])
        mgr.open()
        mgr.close()
        assert dev.disconnect_called

    def test_close_calls_disconnect_in_reverse_order(self):
        order: list[str] = []

        class TrackDevice(MockDevice):
            def disconnect(self):
                order.append(self.name)

        d1, d2 = TrackDevice("first"), TrackDevice("second")
        mgr = HardwareManager([d1, d2])
        mgr.open()
        mgr.close()
        assert order == ["second", "first"]

    def test_context_manager_opens_and_closes(self):
        dev = MockDevice()
        with HardwareManager([dev]) as handles:
            assert dev.connect_called
            assert "mock" in handles
        assert dev.disconnect_called

    def test_preflight_failure_prevents_connect(self):
        dev = MockDevice(fail_preflight=True)
        with pytest.raises(ValueError, match="preflight failed"):
            HardwareManager([dev]).open()
        assert not dev.connect_called

    def test_preflight_failure_does_not_open_subsequent_devices(self):
        bad = MockDevice("bad", fail_preflight=True)
        good = MockDevice("good")
        with pytest.raises(ValueError):
            HardwareManager([bad, good]).open()
        assert not good.connect_called

    def test_disconnect_failure_is_swallowed(self):
        dev = MockDevice(fail_disconnect=True)
        mgr = HardwareManager([dev])
        mgr.open()
        mgr.close()  # must not raise
        assert dev.disconnect_called

    def test_disconnect_failure_does_not_prevent_other_disconnects(self):
        bad = MockDevice("bad", fail_disconnect=True)
        good = MockDevice("good")
        mgr = HardwareManager([bad, good])
        mgr.open()
        mgr.close()
        assert good.disconnect_called

    def test_close_clears_opened_list(self):
        dev = MockDevice()
        mgr = HardwareManager([dev])
        mgr.open()
        mgr.close()
        assert mgr._opened == []

    def test_empty_device_list(self):
        handles = HardwareManager([]).open()
        assert handles == {}


# ---------------------------------------------------------------------------
# BpodDevice


class TestBpodDevice:
    def test_satisfies_device_protocol_structurally(self):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        # runtime_checkable Protocol isinstance invokes property getters via hasattr,
        # which propagates RuntimeError from handle before connect. Check structure
        # directly instead.
        assert BpodDevice.name == "bpod"
        assert callable(BpodDevice.preflight)
        assert callable(BpodDevice.connect)
        assert callable(BpodDevice.disconnect)
        assert isinstance(BpodDevice.handle, property)

    def test_name_is_bpod(self):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        assert BpodDevice(serial_port="/dev/ttyACM0").name == "bpod"

    def test_preflight_raises_on_missing_port(self, tmp_path):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        dev = BpodDevice(serial_port=str(tmp_path / "nonexistent"))
        with pytest.raises(ValueError, match="not accessible"):
            dev.preflight()

    def test_preflight_passes_when_path_exists(self, tmp_path):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        port = tmp_path / "ttyACM0"
        port.touch()
        dev = BpodDevice(serial_port=str(port))
        dev.preflight()  # must not raise

    def test_handle_raises_before_connect(self):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        dev = BpodDevice(serial_port="/dev/ttyACM0")
        with pytest.raises(RuntimeError, match="not connected"):
            _ = dev.handle

    def test_connect_creates_and_opens_factory(self, tmp_path):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        port = tmp_path / "ttyACM0"
        port.touch()
        dev = BpodDevice(serial_port=str(port))
        mock_factory = MagicMock()
        with patch(
            "murineshiftwork.hardware.bpod.device.BpodFactory",
            return_value=mock_factory,
        ):
            dev.connect()
        mock_factory.open.assert_called_once()

    def test_handle_returns_factory_after_connect(self, tmp_path):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        port = tmp_path / "ttyACM0"
        port.touch()
        dev = BpodDevice(serial_port=str(port))
        mock_factory = MagicMock()
        with patch(
            "murineshiftwork.hardware.bpod.device.BpodFactory",
            return_value=mock_factory,
        ):
            dev.connect()
        assert dev.handle is mock_factory

    def test_disconnect_calls_close_safely(self, tmp_path):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        port = tmp_path / "ttyACM0"
        port.touch()
        dev = BpodDevice(serial_port=str(port))
        mock_factory = MagicMock()
        with patch(
            "murineshiftwork.hardware.bpod.device.BpodFactory",
            return_value=mock_factory,
        ):
            dev.connect()
        dev.disconnect()
        mock_factory.close_safely.assert_called_once()

    def test_disconnect_before_connect_is_safe(self):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        dev = BpodDevice(serial_port="/dev/ttyACM0")
        dev.disconnect()  # must not raise

    def test_factory_kwargs_forwarded(self, tmp_path):
        from murineshiftwork.hardware.bpod.device import BpodDevice

        port = tmp_path / "ttyACM0"
        port.touch()
        dev = BpodDevice(serial_port=str(port), connect_retries=5, retry_delay_s=0.1)
        with patch("murineshiftwork.hardware.bpod.device.BpodFactory") as MockFactory:
            MockFactory.return_value = MagicMock()
            dev.connect()
        MockFactory.assert_called_once_with(
            serial_port=str(port), connect_retries=5, retry_delay_s=0.1
        )


# ---------------------------------------------------------------------------
# TaskProcess.devices kwarg injection


class TestTaskProcessDevicesInjection:
    def test_devices_dict_injects_bpod(self, tmp_path):
        """TaskProcess uses devices['bpod'] when bpod= is not provided."""
        from murineshiftwork.hardware.bpod.sim import SimBpod
        from murineshiftwork.logic.task_process import TaskProcess

        sim = SimBpod()
        sim.open()

        tp = TaskProcess(
            serial_port_bpod=None,
            out_path=str(tmp_path / "data"),
            subject="_test_subject",
            task="_test_flush_valves",
            devices={"bpod": sim},
            auto_init=False,
            auto_start=False,
            require_bpod=False,
            settings__task__patched={},
        )
        assert tp.bpod is sim
        assert tp.serial_is_open is True

    def test_explicit_bpod_takes_priority_over_devices(self, tmp_path):
        """bpod= kwarg wins over devices dict."""
        from murineshiftwork.hardware.bpod.sim import SimBpod
        from murineshiftwork.logic.task_process import TaskProcess

        sim_explicit = SimBpod()
        sim_explicit.open()
        sim_in_devices = SimBpod()
        sim_in_devices.open()

        tp = TaskProcess(
            serial_port_bpod=None,
            out_path=str(tmp_path / "data"),
            subject="_test_subject",
            task="_test_flush_valves",
            bpod=sim_explicit,
            devices={"bpod": sim_in_devices},
            auto_init=False,
            auto_start=False,
            require_bpod=False,
        )
        assert tp.bpod is sim_explicit

    def test_devices_without_bpod_key_leaves_bpod_none(self, tmp_path):
        """devices dict with no 'bpod' key falls through to self-managed path."""
        from murineshiftwork.logic.task_process import TaskProcess

        tp = TaskProcess(
            serial_port_bpod=None,
            out_path=str(tmp_path / "data"),
            subject="_test_subject",
            task="_test_flush_valves",
            devices={"scale": object()},
            auto_init=False,
            auto_start=False,
            require_bpod=False,
        )
        assert tp.bpod is None
