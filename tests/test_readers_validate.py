"""Tests for readers.validate.validate_session using checked-in fixture sessions.

Tests run against both JSONL and PKL fixtures. RCE file checks are skipped
because rpi_camera_ensemble is not installed in the test environment.
"""

from pathlib import Path

import pytest

from murineshiftwork.readers.validate import ValidationResult, validate_session

FIXTURES_DIR = Path(__file__).parent / "data"


def _session_dir(variant="jsonl"):
    d = FIXTURES_DIR / f"fixture_{variant}"
    if not d.exists():
        pytest.skip(f"Fixture dir absent: {d}")
    return d


# ---------------------------------------------------------------------------
# Return type and structure


def test_validate_returns_validation_result_jsonl():
    result = validate_session(_session_dir("jsonl"), verbose=False)
    assert isinstance(result, ValidationResult)


def test_validate_returns_validation_result_pkl():
    result = validate_session(_session_dir("pkl"), verbose=False)
    assert isinstance(result, ValidationResult)


# ---------------------------------------------------------------------------
# MSW completeness (no RCE → no TTL checks; just file presence)


def test_validate_jsonl_msw_complete():
    result = validate_session(_session_dir("jsonl"), verbose=False)
    msw_issues = [i for i in result.issues if "MSW" in i or "read_session" in i]
    assert not msw_issues, f"MSW completeness issues: {msw_issues}"


def test_validate_pkl_msw_complete():
    result = validate_session(_session_dir("pkl"), verbose=False)
    msw_issues = [i for i in result.issues if "MSW" in i or "read_session" in i]
    assert not msw_issues, f"MSW completeness issues: {msw_issues}"


def test_validate_jsonl_passes():
    result = validate_session(_session_dir("jsonl"), verbose=False)
    assert result.passed, f"Validation failed: {result.issues}"


def test_validate_pkl_passes():
    result = validate_session(_session_dir("pkl"), verbose=False)
    assert result.passed, f"Validation failed: {result.issues}"


# ---------------------------------------------------------------------------
# Version and metadata


def test_validate_jsonl_version_known():
    result = validate_session(_session_dir("jsonl"), verbose=False)
    assert result.msw_version != "unknown"


def test_validate_rce_not_present_in_fixtures():
    # Fixture sessions have no RCE files — validator should not fail on absence
    result = validate_session(_session_dir("jsonl"), verbose=False)
    assert not result.is_rce_session
