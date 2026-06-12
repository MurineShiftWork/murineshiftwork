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


def test_load_session_opto_host_block_normalized_to_session_name():
    """Old fixture uses parent_acquisition.acquisition_name — must load as session_name."""
    from murineshiftwork.readers import load_session

    d = _skip_if_absent(
        FIXTURES_DIR
        / "fixture_optotagging/_test_subject__20260527_133053_901389__optotagging"
    )
    s = load_session(d)
    # raw key from old YAML must be gone; canonical key must be present
    assert "acquisition_name" not in (s.settings_ephys or {})
    assert s.host_session_name == "_test_oe_controller__20260527_132639__ephys"


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


def test_load_acquisition_uses_manifest_basename_key(tmp_path):
    """acquisition_manifest.yaml with 'basename' key is read correctly."""
    import yaml

    from murineshiftwork.readers import load_acquisition

    # Build a minimal session container with a real acquisition dir inside
    session_basename = "_test_subject__20260527_133053_901389__optotagging"
    acq_dir = tmp_path
    (acq_dir / session_basename).symlink_to(
        FIXTURES_DIR / "fixture_optotagging" / session_basename
    )
    # Write the manifest using the current schema key ("basename")
    manifest = {
        "msw_manifest_version": 1,
        "type": "acquisition",
        "acquisition_name": session_basename,
        "sessions": [
            {"basename": session_basename, "status": "complete", "ended_at": None}
        ],
    }
    (acq_dir / "acquisition_manifest.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False)
    )
    sessions = load_acquisition(acq_dir)
    assert len(sessions) == 1
    assert sessions[0].subject == "_test_subject"


def test_load_acquisition_manifest_session_dir_key_backward_compat(tmp_path):
    """acquisition_manifest.yaml with legacy 'session_dir' key is still read."""
    import yaml

    from murineshiftwork.readers import load_acquisition

    session_basename = "_test_subject__20260527_133053_901389__optotagging"
    acq_dir = tmp_path
    (acq_dir / session_basename).symlink_to(
        FIXTURES_DIR / "fixture_optotagging" / session_basename
    )
    # Write the manifest using the old schema key ("session_dir")
    manifest = {
        "msw_manifest_version": 1,
        "type": "acquisition",
        "sessions": [{"session_dir": session_basename, "status": "complete"}],
    }
    (acq_dir / "acquisition_manifest.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False)
    )
    sessions = load_acquisition(acq_dir)
    assert len(sessions) == 1


# ---------------------------------------------------------------------------
# load_subject — 2-level (legacy) and 3-level (current) directory layouts


def test_load_subject_2level_returns_sessions(tmp_path):
    from murineshiftwork.readers import load_subject

    # legacy backward compat: old standalone data without a session container
    session_basename = (
        "subject001__20260508_172956_258756__probabilistic_switching_fixedsubjects"
    )
    (tmp_path / session_basename).symlink_to(FIXTURES_DIR / "fixture_jsonl")
    sessions = load_subject(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].subject == "subject001"


def test_load_subject_3level_returns_sessions(tmp_path):
    from murineshiftwork.readers import load_subject

    # current layout: subject_dir / session_container / acquisition_dir /
    acq_name = "_test_oe_controller__20260527_132639__ephys"
    session_basename = "_test_subject__20260527_133053_901389__optotagging"
    acq_dir = tmp_path / acq_name
    acq_dir.mkdir()
    (acq_dir / session_basename).symlink_to(
        FIXTURES_DIR / "fixture_optotagging" / session_basename
    )
    sessions = load_subject(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].is_ephys is True
    assert sessions[0].acquisition_name == acq_name


def test_load_subject_3level_sets_acquisition_context(tmp_path):
    from murineshiftwork.readers import load_subject

    acq_name = "_test_oe_controller__20260527_132639__ephys"
    session_basename = "_test_subject__20260527_133053_901389__optotagging"
    acq_dir = tmp_path / acq_name
    acq_dir.mkdir()
    (acq_dir / session_basename).symlink_to(
        FIXTURES_DIR / "fixture_optotagging" / session_basename
    )
    sessions = load_subject(tmp_path)
    assert sessions[0].acquisition_dir == acq_dir


def test_load_subject_3level_standalone_session_prefix(tmp_path):
    """Standalone sessions use a session_ prefix container — must load as 3-level."""
    from murineshiftwork.readers import load_subject

    # fixture_jsonl basename: subject001__20260508_172956_258756__probabilistic_switching_fixedsubjects
    acq_basename = (
        "subject001__20260508_172956_258756__probabilistic_switching_fixedsubjects"
    )
    session_container = "subject001__20260508_172956_258756__session_probabilistic_switching_fixedsubjects"
    container_dir = tmp_path / session_container
    container_dir.mkdir()
    (container_dir / acq_basename).symlink_to(FIXTURES_DIR / "fixture_jsonl")

    sessions = load_subject(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].subject == "subject001"
    assert sessions[0].acquisition_name == session_container
    assert sessions[0].acquisition_dir == container_dir


def test_load_subject_mixed_depths_includes_standalone_session_prefix(tmp_path):
    """2-level legacy dir alongside a standalone session_ prefix 3-level container."""
    from murineshiftwork.readers import load_subject

    # 2-level legacy: another subject dir with .msw. files directly
    s2 = "subject001__20260508_172956_258756__probabilistic_switching_fixedsubjects"
    (tmp_path / s2).symlink_to(FIXTURES_DIR / "fixture_jsonl")

    # 3-level standalone with session_ prefix container
    acq_basename = "_test_subject__20260527_133053_901389__optotagging"
    session_container = "_test_subject__20260527_133053_901389__session_optotagging"
    container_dir = tmp_path / session_container
    container_dir.mkdir()
    (container_dir / acq_basename).symlink_to(
        FIXTURES_DIR / "fixture_optotagging" / acq_basename
    )

    sessions = load_subject(tmp_path)
    assert len(sessions) == 2
    standalone_sessions = [s for s in sessions if s.acquisition_name is None]
    nested_sessions = [s for s in sessions if s.acquisition_name == session_container]
    assert len(standalone_sessions) == 1
    assert len(nested_sessions) == 1


def test_load_subject_mixed_depths(tmp_path):
    from murineshiftwork.readers import load_subject

    # legacy 2-level standalone alongside current 3-level host-linked session
    s2 = "subject001__20260508_172956_258756__probabilistic_switching_fixedsubjects"
    (tmp_path / s2).symlink_to(FIXTURES_DIR / "fixture_jsonl")

    acq_dir = tmp_path / "_test_oe_controller__20260527_132639__ephys"
    acq_dir.mkdir()
    s3 = "_test_subject__20260527_133053_901389__optotagging"
    (acq_dir / s3).symlink_to(FIXTURES_DIR / "fixture_optotagging" / s3)

    sessions = load_subject(tmp_path)
    assert len(sessions) == 2
    subjects = {s.subject for s in sessions}
    assert "subject001" in subjects
    assert "_test_subject" in subjects
