"""Tests for logagent/logagent.py (LogAgent) and logagent/server.py."""

import multiprocessing

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from murineshiftwork.logagent.logagent import LogAgent  # noqa: E402
from murineshiftwork.logagent.server import create_app  # noqa: E402

_START_PAYLOAD = {
    "subject": "mouse001",
    "task": "sequence",
    "setup": "rig-a",
    "session_uuid": "test-uuid-1234",
}


# ---------------------------------------------------------------------------
# LogAgent tests


class TestLogAgent:
    def test_is_daemon_process(self):
        q = multiprocessing.Queue(maxsize=10)
        agent = LogAgent(q, "http://localhost:8080", "rig-a", _START_PAYLOAD)
        assert agent.daemon is True

    def test_stops_on_none_sentinel(self):
        q = multiprocessing.Queue(maxsize=10)
        agent = LogAgent(q, "http://localhost:9999", "rig-a", _START_PAYLOAD)
        agent.start()
        assert agent.is_alive()
        q.put(None)
        agent.join(timeout=3)
        assert not agent.is_alive()

    def test_stops_on_stop_sentinel_dict(self):
        q = multiprocessing.Queue(maxsize=10)
        agent = LogAgent(q, "http://localhost:9999", "rig-a", _START_PAYLOAD)
        agent.start()
        q.put({"__stop__": True, "summary": {"trial_count": 10}})
        agent.join(timeout=3)
        assert not agent.is_alive()

    def test_strips_url_trailing_slash(self):
        q = multiprocessing.Queue(maxsize=10)
        agent = LogAgent(q, "http://localhost:8080/", "rig-a", _START_PAYLOAD)
        assert agent._log_url == "http://localhost:8080"

    def test_drops_silently_when_server_unreachable(self):
        q = multiprocessing.Queue(maxsize=10)
        agent = LogAgent(q, "http://127.0.0.1:19999", "rig-a", _START_PAYLOAD)
        agent.start()
        q.put({"trial_index": 1, "outcome": "correct"})
        q.put(None)
        agent.join(timeout=5)
        assert not agent.is_alive()

    def test_full_queue_put_nowait_raises(self):
        q = multiprocessing.Queue(maxsize=2)
        q.put({"trial_index": 0})
        q.put({"trial_index": 1})
        with pytest.raises(Exception):
            q.put_nowait({"trial_index": 2})

    def test_post_url_format(self):
        q = multiprocessing.Queue(maxsize=1)
        agent = LogAgent(q, "http://host:8080", "my-rig", _START_PAYLOAD)
        url = f"{agent._log_url}/ingest/{agent._setup}/trial"
        assert url == "http://host:8080/ingest/my-rig/trial"

    def test_bearer_token_stored(self):
        q = multiprocessing.Queue(maxsize=1)
        agent = LogAgent(
            q, "http://localhost:8080", "rig-a", _START_PAYLOAD, bearer_token="secret"
        )
        assert agent._bearer_token == "secret"

    def test_no_bearer_token_by_default(self):
        q = multiprocessing.Queue(maxsize=1)
        agent = LogAgent(q, "http://localhost:8080", "rig-a", _START_PAYLOAD)
        assert agent._bearer_token == ""

    def test_session_uuid_stored(self):
        q = multiprocessing.Queue(maxsize=1)
        agent = LogAgent(
            q,
            "http://localhost:8080",
            "rig-a",
            _START_PAYLOAD,
            session_uuid="abc-123",
        )
        assert agent._session_uuid == "abc-123"


# ---------------------------------------------------------------------------
# Monitor server tests


class TestMonitorServer:
    def setup_method(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_health(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ingest_start_creates_session(self):
        resp = self.client.post(
            "/ingest/rig-test/start",
            json={"subject": "mouse001", "task": "sequence"},
        )
        assert resp.status_code == 204

    def test_status_after_start(self):
        self.client.post(
            "/ingest/rig-test/start",
            json={
                "subject": "mouse001",
                "task": "sequence",
                "started_at": "2026-05-23T12:00:00+00:00",
            },
        )
        resp = self.client.get("/session/status/rig-test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "running"
        assert data["subject"] == "mouse001"
        assert data["trial_count"] == 0

    def test_session_uuid_stored_from_start_payload(self):
        self.client.post(
            "/ingest/rig-uuid/start",
            json={"subject": "m1", "task": "seq", "session_uuid": "uuid-abc"},
        )
        data = self.client.get("/session/status/rig-uuid").json()
        assert data["session_uuid"] == "uuid-abc"

    def test_ingest_trial_wrapped_in_trial_data(self):
        """LogAgent sends {trial_data: {...}}; server unwraps for storage."""
        self.client.post(
            "/ingest/rig-t2/start",
            json={"subject": "mouse002", "task": "sequence"},
        )
        for i in range(5):
            self.client.post(
                "/ingest/rig-t2/trial",
                json={
                    "trial_data": {
                        "trial_index": i,
                        "outcome": "correct",
                        "reward_count_trial": 1,
                        "liquid_ul_trial": 3.0,
                    }
                },
            )
        resp = self.client.get("/session/status/rig-t2")
        data = resp.json()
        assert data["trial_count"] == 5
        assert data["reward_count"] == 5
        assert data["liquid_ul"] == pytest.approx(15.0)

    def test_ingest_trial_flat_body_still_works(self):
        """Flat body (no trial_data wrapper) is accepted for backward compat."""
        self.client.post(
            "/ingest/rig-t2b/start",
            json={"subject": "mouse002", "task": "sequence"},
        )
        self.client.post(
            "/ingest/rig-t2b/trial",
            json={"trial_index": 0, "reward_count_trial": 1, "liquid_ul_trial": 2.0},
        )
        resp = self.client.get("/session/status/rig-t2b")
        assert resp.json()["trial_count"] == 1

    def test_ingest_stop_sets_idle(self):
        self.client.post(
            "/ingest/rig-t3/start",
            json={"subject": "mouse003", "task": "sequence"},
        )
        self.client.post("/ingest/rig-t3/stop", json={})
        assert self.client.get("/session/status/rig-t3").json()["state"] == "idle"

    def test_status_all(self):
        self.client.post("/ingest/rig-a1/start", json={"subject": "m1", "task": "seq"})
        self.client.post("/ingest/rig-b1/start", json={"subject": "m2", "task": "seq"})
        resp = self.client.get("/session/status")
        assert "rig-a1" in resp.json()
        assert "rig-b1" in resp.json()

    def test_status_404_for_unknown_setup(self):
        assert self.client.get("/session/status/does-not-exist-xyz").status_code == 404

    def test_start_clears_previous_trial_buffer(self):
        self.client.post("/ingest/rig-t4/start", json={"subject": "m1", "task": "s"})
        for i in range(3):
            self.client.post(
                "/ingest/rig-t4/trial",
                json={
                    "trial_data": {
                        "trial_index": i,
                        "reward_count_trial": 1,
                        "liquid_ul_trial": 2.0,
                    }
                },
            )
        self.client.post("/ingest/rig-t4/start", json={"subject": "m2", "task": "s"})
        assert self.client.get("/session/status/rig-t4").json()["trial_count"] == 0

    def test_reward_count_zero_when_no_trials(self):
        self.client.post("/ingest/rig-t5/start", json={"subject": "m1", "task": "s"})
        data = self.client.get("/session/status/rig-t5").json()
        assert data["reward_count"] == 0
        assert data["liquid_ul"] == pytest.approx(0.0)

    def test_elapsed_s_present_after_start(self):
        self.client.post(
            "/ingest/rig-t6/start",
            json={
                "subject": "m1",
                "task": "s",
                "started_at": "2020-01-01T00:00:00+00:00",
            },
        )
        data = self.client.get("/session/status/rig-t6").json()
        assert data["elapsed_s"] is not None
        assert data["elapsed_s"] > 0


class TestMonitorServerAuth:
    def setup_method(self):
        self.app = create_app(bearer_token="secret-token")
        self.client = TestClient(self.app)

    def test_ingest_start_requires_token(self):
        resp = self.client.post(
            "/ingest/rig-auth/start", json={"subject": "m1", "task": "s"}
        )
        assert resp.status_code == 401

    def test_ingest_start_with_correct_token(self):
        resp = self.client.post(
            "/ingest/rig-auth/start",
            json={"subject": "m1", "task": "s"},
            headers={"Authorization": "Bearer secret-token"},
        )
        assert resp.status_code == 204

    def test_ingest_start_with_wrong_token(self):
        resp = self.client.post(
            "/ingest/rig-auth/start",
            json={"subject": "m1", "task": "s"},
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401

    def test_health_no_auth_required(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200

    def test_status_no_auth_required(self):
        resp = self.client.get("/session/status")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TaskProcess relay integration


def test_task_process_starts_log_agent_when_log_url_set(monkeypatch):
    """TaskProcess creates relay_queue and starts LogAgent when log_url is set."""
    import sys
    import types

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
