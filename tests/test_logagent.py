"""Integration tests for TaskProcess relay (LogAgent wiring in msw-core).

These tests verify that TaskProcess._start_relay() and exit_safely() wire
the relay queue correctly.  They monkeypatch the logagent import so msw-agent
does not need to be installed.

LogAgent unit tests and server tests live in msw-agent/tests/test_logagent.py.
"""

import multiprocessing
import types


def test_task_process_starts_log_agent_when_log_url_set(monkeypatch):
    """TaskProcess creates relay_queue and starts LogAgent when log_url is set."""
    import sys

    import murineshiftwork.logic.task_process as tp_mod

    monkeypatch.setattr(
        "murineshiftwork.logic.machine_config._load_machine_config",
        lambda: {"log_url": "http://localhost:8080", "log_bearer_token": "tok"},
    )

    started = []

    class FakeLogAgent:
        daemon = True

        def __init__(
            self,
            queue,
            log_url,
            setup,
            session_start_payload,
            session_uuid="",
            bearer_token="",
        ):
            self.queue = queue
            self.log_url = log_url
            self.setup = setup
            self.payload = session_start_payload
            self.session_uuid = session_uuid
            self.bearer_token = bearer_token
            started.append(self)

        def start(self):
            pass

    fake_mod = types.ModuleType("murineshiftwork.logagent.logagent")
    fake_mod.LogAgent = FakeLogAgent
    monkeypatch.setitem(sys.modules, "murineshiftwork.logagent.logagent", fake_mod)

    tp = object.__new__(tp_mod.TaskProcess)
    tp._relay_queue = None
    tp._relay_proc = None
    tp.subject = "mouse001"
    tp.task_name = "sequence"
    tp.session_uuid = "uuid-test-abc"
    tp.session_paths = {"session_folder": "/tmp/s", "session_basename": "s"}
    tp.input_kwargs = {"setup": "rig-a"}
    tp._start_relay()

    assert tp._relay_queue is not None
    assert tp.input_kwargs.get("relay_queue") is tp._relay_queue
    assert len(started) == 1
    agent = started[0]
    assert agent.setup == "rig-a"
    assert agent.payload["subject"] == "mouse001"
    assert agent.payload["task"] == "sequence"
    assert agent.payload["session_uuid"] == "uuid-test-abc"
    assert "started_at" in agent.payload
    assert agent.session_uuid == "uuid-test-abc"
    assert agent.bearer_token == "tok"


def test_task_process_no_relay_when_no_log_url(monkeypatch):
    import murineshiftwork.logic.task_process as tp_mod

    monkeypatch.setattr(
        "murineshiftwork.logic.machine_config._load_machine_config",
        lambda: {},
    )
    tp = object.__new__(tp_mod.TaskProcess)
    tp._relay_queue = None
    tp._relay_proc = None
    tp.input_kwargs = {}
    tp._start_relay()

    assert tp._relay_queue is None
    assert "relay_queue" not in tp.input_kwargs


def test_exit_safely_sends_none_sentinel():
    """exit_safely() puts None into relay_queue so LogAgent sends session stop."""
    import murineshiftwork.logic.task_process as tp_mod

    tp = object.__new__(tp_mod.TaskProcess)
    tp.exiting = False
    tp.serial_is_open = False
    tp.bpod = None
    q = multiprocessing.Queue(maxsize=10)
    tp._relay_queue = q
    tp.exit_safely()

    assert tp._relay_queue is None
    assert q.get(timeout=2) is None
