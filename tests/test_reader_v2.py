"""Tests for the v2 .msw.session.yaml reader format.

Fixture source: real hardware session from _test_subject on setup-1,
2026-05-16, probabilistic_switching_fixedsubjects (23 trials, short test run).
Settings hand-converted from v1 JSON files to v2 YAML format using the
synthesis script in tests/data/fixture_v2/generate_fixture.py.

Files:
  _test_subject__20260516_130611_739182__probabilistic_switching_fixedsubjects.msw.session.yaml
  _test_subject__20260516_130611_739182__probabilistic_switching_fixedsubjects.msw.df.jsonl
  _test_subject__20260516_130611_739182__probabilistic_switching_fixedsubjects.msw.csv
"""

from pathlib import Path

import pytest

from murineshiftwork.readers.session import read_session_data

FIXTURE_V2 = Path(__file__).parent / "data" / "fixture_v2"
_skip_no_fixture = pytest.mark.skipif(
    not FIXTURE_V2.exists(),
    reason="fixture_v2 directory absent",
)


@_skip_no_fixture
class TestReaderV2Format:
    def test_fixture_dir_exists(self):
        assert FIXTURE_V2.exists(), "fixture_v2 directory must exist"

    def test_session_loads_without_error(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        assert isinstance(data, dict)

    def test_msw_version_correct(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        assert data["msw_version"] == "1.0.0"

    def test_settings_process_populated(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        proc = data.get("settings.process")
        assert proc is not None, "settings.process must be present for v2 format"
        assert proc["task"] == "probabilistic_switching_fixedsubjects"
        assert proc["subject"] == "_test_subject"
        assert proc["setup"] == "setup-1"

    def test_settings_task_populated(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        ts = data.get("settings.task")
        assert ts is not None, "settings.task must be present for v2 format"
        assert "reward_amount_ul" in ts or "HARDWARE_VALVES_FOR_WATER" in ts

    def test_settings_stage_populated(self):
        """This fixture includes stage config from the real session."""
        data = read_session_data(session_dir=FIXTURE_V2)
        assert "settings.stage" in data, "stage section must be present in this fixture"

    def test_df_loaded(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        df = data.get("df")
        assert df is not None, "trial dataframe must be loaded"
        assert len(df) >= 1

    def test_is_complete_session(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        assert data["is_complete_session"] is True

    def test_is_not_legacy_session(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        assert data["is_legacy_session"] is False

    def test_not_ephys_session(self):
        data = read_session_data(session_dir=FIXTURE_V2)
        assert data["is_ephys_session"] is False


@pytest.mark.skipif(
    not (Path(__file__).parent / "data" / "fixture_jsonl").exists(),
    reason="fixture_jsonl not in repo (tests/data/ is gitignored)",
)
class TestReaderBackwardCompatJSONL:
    """Confirm fixture_jsonl (v1 JSON format) still reads correctly."""

    FIXTURE_JSONL = Path(__file__).parent / "data" / "fixture_jsonl"

    def test_jsonl_session_loads(self):
        data = read_session_data(session_dir=self.FIXTURE_JSONL)
        assert isinstance(data, dict)

    def test_jsonl_has_settings_process(self):
        data = read_session_data(session_dir=self.FIXTURE_JSONL)
        assert "settings.process" in data

    def test_jsonl_has_settings_task(self):
        data = read_session_data(session_dir=self.FIXTURE_JSONL)
        assert "settings.task" in data

    def test_jsonl_msw_version_set(self):
        data = read_session_data(session_dir=self.FIXTURE_JSONL)
        assert "msw_version" in data
        assert data["msw_version"] not in ("legacy",)
