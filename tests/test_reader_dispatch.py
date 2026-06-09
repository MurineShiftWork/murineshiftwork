"""Tests for read_session_data() dispatch routing via _READER_DISPATCH."""

from pathlib import Path
from unittest.mock import patch

import pytest

from murineshiftwork.readers.namespace import (
    ARTIFACT_FORMAT_LEGACY,
    ARTIFACT_FORMAT_SEPARATE_JSON,
    ARTIFACT_FORMAT_SESSION_YAML,
)
from murineshiftwork.readers.session import (
    _READER_DISPATCH,
    _check_completeness,
    _read_legacy,
    _read_separate_json,
    _read_session_yaml,
    read_session_data,
)

FIXTURES_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# _READER_DISPATCH registration


def test_dispatch_covers_all_three_formats():
    assert ARTIFACT_FORMAT_SESSION_YAML in _READER_DISPATCH
    assert ARTIFACT_FORMAT_SEPARATE_JSON in _READER_DISPATCH
    assert ARTIFACT_FORMAT_LEGACY in _READER_DISPATCH


def test_dispatch_functions_are_callable():
    for fn in _READER_DISPATCH.values():
        assert callable(fn)


def test_dispatch_routes_to_session_yaml_reader():
    assert _READER_DISPATCH[ARTIFACT_FORMAT_SESSION_YAML] is _read_session_yaml


def test_dispatch_routes_to_separate_json_reader():
    assert _READER_DISPATCH[ARTIFACT_FORMAT_SEPARATE_JSON] is _read_separate_json


def test_dispatch_routes_to_legacy_reader():
    assert _READER_DISPATCH[ARTIFACT_FORMAT_LEGACY] is _read_legacy


# ---------------------------------------------------------------------------
# _check_completeness


def test_completeness_passes_with_all_keys():
    data = {"df": object(), "settings.task": {}, "settings.process": {}}
    assert _check_completeness(data, is_legacy=False)


def test_completeness_fails_missing_df():
    data = {"settings.task": {}, "settings.process": {}}
    assert not _check_completeness(data, is_legacy=False)


def test_completeness_fails_none_df():
    data = {"df": None, "settings.task": {}, "settings.process": {}}
    assert not _check_completeness(data, is_legacy=False)


def test_completeness_fails_missing_settings_process_nonlegacy():
    data = {"df": object(), "settings.task": {}}
    assert not _check_completeness(data, is_legacy=False)


def test_completeness_passes_without_settings_process_for_legacy():
    data = {"df": object(), "settings.task": {}}
    assert _check_completeness(data, is_legacy=True)


def test_completeness_passes_without_raw_key():
    data = {"df": object(), "settings.task": {}, "settings.process": {}}
    assert _check_completeness(data, is_legacy=False)


# ---------------------------------------------------------------------------
# read_session_data() — format metadata always present in output


@pytest.mark.parametrize(
    "fixture",
    [
        "fixture_pkl",
        "fixture_jsonl",
        "fixture_v2",
        "fixture_fixedsubjects",
        "fixture_sequence",
    ],
)
def test_format_keys_present(fixture):
    d = read_session_data(FIXTURES_DIR / fixture)
    assert "namespace_version" in d
    assert "artifact_format" in d
    assert "is_legacy_session" in d
    assert "msw_version" in d
    assert "is_complete_session" in d


@pytest.mark.parametrize(
    "fixture", ["fixture_v2", "fixture_fixedsubjects", "fixture_sequence"]
)
def test_session_yaml_fixtures_are_complete(fixture):
    d = read_session_data(FIXTURES_DIR / fixture)
    assert d["artifact_format"] == ARTIFACT_FORMAT_SESSION_YAML
    assert d["is_complete_session"]


@pytest.mark.parametrize("fixture", ["fixture_pkl", "fixture_jsonl"])
def test_separate_json_fixtures_detected(fixture):
    d = read_session_data(FIXTURES_DIR / fixture)
    assert d["artifact_format"] == ARTIFACT_FORMAT_SEPARATE_JSON


def test_unknown_format_raises():

    with (
        patch(
            "murineshiftwork.readers.session.detect_session_format",
            return_value={
                "artifact_format": "unknown_format",
                "namespace_version": None,
            },
        ),
        patch(
            "murineshiftwork.readers.session.test_is_legacy_format", return_value=False
        ),
        pytest.raises(ValueError, match="No reader registered"),
    ):
        read_session_data(FIXTURES_DIR / "fixture_v2")
