"""Tests for readers.batch — load_session / load_acquisition / load_subject."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "data"


def _skip_if_absent(d: Path) -> Path:
    if not d.exists():
        pytest.skip(f"Fixture absent: {d}")
    return d


# ---------------------------------------------------------------------------
# load_session — fixture coverage


@pytest.mark.parametrize(
    "rel_path",
    [
        "fixture_jsonl",
        "fixture_pkl",
        "fixture_legacy/subject003__20210426_183409__probabilistic_switching",
        "fixture_optotagging/_test_subject__20260527_133053_901389__optotagging",
    ],
    ids=["jsonl", "pkl", "legacy", "optotagging"],
)
def test_load_session_returns_msw_session(rel_path):
    from murineshiftwork.readers import MswSession, load_session

    d = _skip_if_absent(FIXTURES_DIR / rel_path)
    s = load_session(d)
    assert isinstance(s, MswSession)


@pytest.mark.parametrize(
    "rel_path,expected_subject",
    [
        ("fixture_jsonl", "subject001"),
        ("fixture_pkl", "subject002"),
        (
            "fixture_legacy/subject003__20210426_183409__probabilistic_switching",
            "subject003",
        ),
        (
            "fixture_optotagging/_test_subject__20260527_133053_901389__optotagging",
            "_test_subject",
        ),
    ],
    ids=["jsonl", "pkl", "legacy", "optotagging"],
)
def test_load_session_subject(rel_path, expected_subject):
    from murineshiftwork.readers import load_session

    d = _skip_if_absent(FIXTURES_DIR / rel_path)
    s = load_session(d)
    assert s.subject == expected_subject


def test_load_session_legacy_task_settings_in_model():
    from murineshiftwork.readers import load_session

    d = _skip_if_absent(
        FIXTURES_DIR
        / "fixture_legacy/subject003__20210426_183409__probabilistic_switching"
    )
    s = load_session(d)
    assert s.settings_task is not None
    assert "PROBABILITIES" in s.settings_task


def test_load_session_opto_ephys_in_model():
    from murineshiftwork.readers import load_session

    d = _skip_if_absent(
        FIXTURES_DIR
        / "fixture_optotagging/_test_subject__20260527_133053_901389__optotagging"
    )
    s = load_session(d)
    assert s.is_ephys is True
    assert s.settings_ephys is not None
    assert s.settings_ephys["backend"] == "open_ephys"


def test_load_session_to_dict_has_required_keys():
    from murineshiftwork.readers import load_session

    d = _skip_if_absent(FIXTURES_DIR / "fixture_jsonl")
    s = load_session(d)
    out = s.to_dict()
    for key in (
        "session_dir",
        "basename",
        "subject",
        "task",
        "artifact_format",
        "msw_version",
        "is_complete",
        "is_ephys",
    ):
        assert key in out, f"Missing key: {key}"


def test_load_session_df_is_dataframe_or_none():
    from murineshiftwork.readers import load_session

    d = _skip_if_absent(FIXTURES_DIR / "fixture_jsonl")
    s = load_session(d)
    assert s.df is None or isinstance(s.df, pd.DataFrame)


def test_load_session_acquisition_context_none_by_default():
    from murineshiftwork.readers import load_session

    d = _skip_if_absent(FIXTURES_DIR / "fixture_jsonl")
    s = load_session(d)
    assert s.acquisition_name is None
    assert s.acquisition_dir is None


# ---------------------------------------------------------------------------
# load_acquisition — using the optotagging acquisition fixture


def _opto_acquisition_dir():
    return _skip_if_absent(FIXTURES_DIR / "fixture_optotagging")


def test_load_acquisition_returns_list():
    from murineshiftwork.readers import load_acquisition

    sessions = load_acquisition(_opto_acquisition_dir())
    assert isinstance(sessions, list)


def test_load_acquisition_sessions_have_acquisition_name():
    from murineshiftwork.readers import load_acquisition

    sessions = load_acquisition(_opto_acquisition_dir())
    assert len(sessions) >= 1
    for s in sessions:
        assert s.acquisition_name is not None
        assert s.acquisition_dir is not None


def test_load_acquisition_sessions_sorted():
    from murineshiftwork.readers import load_acquisition

    sessions = load_acquisition(_opto_acquisition_dir())
    datetimes = [s.datetime_str for s in sessions]
    assert datetimes == sorted(datetimes)
