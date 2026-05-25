"""Retrograde reader framework — session format detection tests.

Parametrized across all tests/data/fixture_* directories so that:
  - every fixture is validated against the MSW namespace spec
  - namespace version (basename datetime format) is detected correctly
  - artifact format (settings storage layout) is detected correctly

Adding a new fixture only requires appending to FIXTURE_EXPECTATIONS.
"""

from pathlib import Path

import pytest

from murineshiftwork.namespace.paths import NAMESPACE_LEGACY, NAMESPACE_V1
from murineshiftwork.readers.namespace import (
    ARTIFACT_FORMAT_LEGACY,
    ARTIFACT_FORMAT_SEPARATE_JSON,
    ARTIFACT_FORMAT_SESSION_YAML,
    detect_artifact_format,
    detect_session_format,
    validate_session_namespace,
)

FIXTURES_DIR = Path(__file__).parent / "data"

# (fixture_dir_name, expected_namespace_version, expected_artifact_format)
FIXTURE_EXPECTATIONS = [
    ("fixture_pkl", NAMESPACE_LEGACY, ARTIFACT_FORMAT_SEPARATE_JSON),
    ("fixture_jsonl", NAMESPACE_V1, ARTIFACT_FORMAT_SEPARATE_JSON),
    ("fixture_v2", NAMESPACE_V1, ARTIFACT_FORMAT_SESSION_YAML),
    ("fixture_fixedsubjects", NAMESPACE_V1, ARTIFACT_FORMAT_SESSION_YAML),
    ("fixture_sequence", NAMESPACE_V1, ARTIFACT_FORMAT_SESSION_YAML),
]

_FIXTURE_IDS = [f[0] for f in FIXTURE_EXPECTATIONS]


def _dir(name: str) -> Path:
    d = FIXTURES_DIR / name
    if not d.exists():
        pytest.skip(f"Fixture absent: {d}")
    return d


# ---------------------------------------------------------------------------
# detect_session_format


@pytest.mark.parametrize("fixture,ns,af", FIXTURE_EXPECTATIONS, ids=_FIXTURE_IDS)
def test_detect_format_has_required_keys(fixture, ns, af):
    result = detect_session_format(_dir(fixture))
    for key in ("basename", "namespace_version", "artifact_format", "parse_error"):
        assert key in result


@pytest.mark.parametrize("fixture,ns,af", FIXTURE_EXPECTATIONS, ids=_FIXTURE_IDS)
def test_detect_namespace_version(fixture, ns, af):
    result = detect_session_format(_dir(fixture))
    assert result["parse_error"] is None, f"parse_error: {result['parse_error']}"
    assert result["namespace_version"] == ns


@pytest.mark.parametrize("fixture,ns,af", FIXTURE_EXPECTATIONS, ids=_FIXTURE_IDS)
def test_detect_artifact_format(fixture, ns, af):
    result = detect_session_format(_dir(fixture))
    assert result["artifact_format"] == af


@pytest.mark.parametrize("fixture,ns,af", FIXTURE_EXPECTATIONS, ids=_FIXTURE_IDS)
def test_detect_basename_is_nonempty(fixture, ns, af):
    result = detect_session_format(_dir(fixture))
    assert result["basename"]
    assert "__" in result["basename"]


# ---------------------------------------------------------------------------
# validate_session_namespace


@pytest.mark.parametrize("fixture,ns,af", FIXTURE_EXPECTATIONS, ids=_FIXTURE_IDS)
def test_validate_namespace_valid(fixture, ns, af):
    v = validate_session_namespace(_dir(fixture))
    assert v["valid"] is True, f"namespace invalid: {v['error']}"
    assert v["error"] is None


@pytest.mark.parametrize("fixture,ns,af", FIXTURE_EXPECTATIONS, ids=_FIXTURE_IDS)
def test_validate_namespace_version_matches_detect(fixture, ns, af):
    v = validate_session_namespace(_dir(fixture))
    d = detect_session_format(_dir(fixture))
    assert v["namespace_version"] == d["namespace_version"]


# ---------------------------------------------------------------------------
# detect_artifact_format (standalone)


@pytest.mark.parametrize("fixture,ns,af", FIXTURE_EXPECTATIONS, ids=_FIXTURE_IDS)
def test_detect_artifact_format_standalone(fixture, ns, af):
    assert detect_artifact_format(_dir(fixture)) == af


# ---------------------------------------------------------------------------
# Negative cases — non-MSW directory


def test_detect_format_non_msw_dir(tmp_path):
    (tmp_path / "random_file.csv").touch()
    result = detect_session_format(tmp_path)
    assert result["artifact_format"] == ARTIFACT_FORMAT_LEGACY
    assert result["namespace_version"] is None
    assert result["parse_error"] is not None


def test_validate_namespace_non_msw_dir(tmp_path):
    v = validate_session_namespace(tmp_path)
    assert v["valid"] is False
    assert v["error"] is not None


# ---------------------------------------------------------------------------
# Artifact format constants are distinct strings


def test_artifact_format_constants_are_distinct():
    formats = [
        ARTIFACT_FORMAT_LEGACY,
        ARTIFACT_FORMAT_SEPARATE_JSON,
        ARTIFACT_FORMAT_SESSION_YAML,
    ]
    assert len(formats) == len(set(formats))
