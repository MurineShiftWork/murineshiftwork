"""Unit tests for murineshiftwork.namespace.

All tests use dummy scalar arguments — no CLI, no hardware, no config files.
"""

from datetime import datetime

import pytest

from murineshiftwork.namespace.paths import (
    _NAMESPACE_FORMATS,
    CURRENT_NAMESPACE_VERSION,
    NAMESPACE_LEGACY,
    NAMESPACE_V1,
    build_data_paths,
    generate_session_paths,
    parse_session_basename,
)

# ---------------------------------------------------------------------------
# Version constants


def test_current_version_is_v1():
    assert CURRENT_NAMESPACE_VERSION == NAMESPACE_V1


def test_v1_format_has_microseconds():
    assert "%f" in _NAMESPACE_FORMATS[NAMESPACE_V1]


def test_legacy_format_has_no_microseconds():
    assert "%f" not in _NAMESPACE_FORMATS[NAMESPACE_LEGACY]


# ---------------------------------------------------------------------------
# generate_session_paths — v1


def test_v1_basename_structure():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_V1, printout=False
    )
    parts = paths["session_basename"].split("__")
    assert len(parts) == 3
    assert parts[0] == "mouse_01"
    assert parts[2] == "flush"


def test_v1_datetime_has_microseconds():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_V1, printout=False
    )
    dt_str = paths["session_basename"].split("__")[1]
    # v1 format: YYYYmmdd_HHMMSS_ffffff  → 22 chars
    assert len(dt_str) == 22
    dt = datetime.strptime(dt_str, _NAMESPACE_FORMATS[NAMESPACE_V1])
    assert isinstance(dt, datetime)


def test_v1_namespace_version_in_result():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_V1, printout=False
    )
    assert paths["namespace_version"] == NAMESPACE_V1


def test_v1_session_folder_path():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_V1, printout=False
    )
    assert paths["session_folder"].startswith("/data/mouse_01/")
    assert "mouse_01__" in paths["session_folder"]
    assert "__flush" in paths["session_folder"]


def test_v1_standalone_acquisition_name():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_V1, printout=False
    )
    assert paths["acquisition_name"].endswith("__session_flush")
    assert f"/{paths['acquisition_name']}/" in paths["session_folder"]


def test_v1_child_session_nesting():
    parent = "mouse_01__20260514_143022_123456__parent_task"
    paths = generate_session_paths(
        "mouse_01",
        "child_task",
        "/data",
        version=NAMESPACE_V1,
        linked_to=parent,
        printout=False,
    )
    assert f"/{parent}/" in paths["session_folder"]


# ---------------------------------------------------------------------------
# generate_session_paths — legacy


def test_legacy_datetime_seconds_only():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_LEGACY, printout=False
    )
    dt_str = paths["session_basename"].split("__")[1]
    # legacy format: YYYYmmdd_HHMMSS  → 15 chars
    assert len(dt_str) == 15
    dt = datetime.strptime(dt_str, _NAMESPACE_FORMATS[NAMESPACE_LEGACY])
    assert isinstance(dt, datetime)


def test_legacy_namespace_version_in_result():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_LEGACY, printout=False
    )
    assert paths["namespace_version"] == NAMESPACE_LEGACY


# ---------------------------------------------------------------------------
# generate_session_paths — validation


def test_unknown_version_raises():
    with pytest.raises(ValueError, match="Unknown namespace version"):
        generate_session_paths(
            "mouse_01", "flush", "/data", version="v99", printout=False
        )


def test_forbidden_chars_in_subject_raise():
    for bad_char in [" ", "#", "@", "!"]:
        with pytest.raises(ValueError, match="forbidden characters"):
            generate_session_paths(
                f"mouse{bad_char}01", "flush", "/data", printout=False
            )


def test_test_task_uses_default_subject():
    paths = generate_session_paths(
        "real_subject",
        "_test__flush",
        "/data",
        version=NAMESPACE_V1,
        printout=False,
    )
    assert paths["subject"] == "_test_subject"


# ---------------------------------------------------------------------------
# build_data_paths — shim


def test_build_data_paths_uses_current_version():
    paths = build_data_paths(
        basepath="/data", subject="mouse_01", task="flush", printout=False
    )
    assert paths["namespace_version"] == CURRENT_NAMESPACE_VERSION


def test_build_data_paths_output_equivalent_to_generate():
    """build_data_paths and generate_session_paths(version=CURRENT) have the same keys."""
    a = build_data_paths(
        basepath="/data", subject="mouse_01", task="flush", printout=False
    )
    b = generate_session_paths("mouse_01", "flush", "/data", printout=False)
    assert set(a.keys()) == set(b.keys())


# ---------------------------------------------------------------------------
# parse_session_basename — version detection


def test_parse_v1_basename():
    basename = "mouse_01__20260514_143022_123456__sequence_automated"
    info = parse_session_basename(basename)
    assert info["namespace_version"] == NAMESPACE_V1
    assert info["subject"] == "mouse_01"
    assert info["task"] == "sequence_automated"
    assert info["datetime"].microsecond == 123456
    assert info["datetime_str"] == "20260514_143022_123456"


def test_parse_legacy_basename():
    basename = "sleep_lhb_c344986_m1097354__20210718_152153__probabilistic_switching"
    info = parse_session_basename(basename)
    assert info["namespace_version"] == NAMESPACE_LEGACY
    assert info["subject"] == "sleep_lhb_c344986_m1097354"
    assert info["task"] == "probabilistic_switching"
    assert info["datetime"].microsecond == 0
    assert info["datetime"].year == 2021


def test_parse_roundtrip_v1():
    """Basename generated by v1 must parse back as v1."""
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_V1, printout=False
    )
    info = parse_session_basename(paths["session_basename"])
    assert info["namespace_version"] == NAMESPACE_V1
    assert info["subject"] == "mouse_01"
    assert info["task"] == "flush"


def test_parse_roundtrip_legacy():
    paths = generate_session_paths(
        "mouse_01", "flush", "/data", version=NAMESPACE_LEGACY, printout=False
    )
    info = parse_session_basename(paths["session_basename"])
    assert info["namespace_version"] == NAMESPACE_LEGACY


def test_parse_wrong_separator_count_raises():
    with pytest.raises(ValueError, match="3 '__'-separated parts"):
        parse_session_basename("bad_name_no_separators")


def test_parse_bad_datetime_raises():
    # "notadatetime" fails the session regex (no \d{8}_\d{6} match), so the
    # builder catches it before the version-detection loop.
    with pytest.raises(ValueError):
        parse_session_basename("mouse_01__notadatetime__flush")
