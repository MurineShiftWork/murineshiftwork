"""Tests for NamespaceBuilder (Pydantic + YAML spec)."""

from pathlib import Path

import pytest

from murineshiftwork.namespace.spec import (
    NamespaceBuilder,
    NamespaceLevelSpec,
    NamespaceSpec,
)

_SPEC_DIR = Path(__file__).parent / "data"

VALUES_V3 = {
    "subject_prefix": "s",
    "subject_id": "082",
    "exp_short_name": "tabfixed",
    "mouse_id": "1099615",
    "ear": "x",
    "date": "20240502",
    "time": "131422",
    "modality": "recording",
    "paradigm": "probabilistic_switching",
    "suffix": "msw",
    "extension": "pkl",
}


# ---------------------------------------------------------------------------
# Spec validation


def test_namespace_spec_invalid_regex():
    with pytest.raises(Exception):
        NamespaceLevelSpec(template="{x}", regex="(?P<x>[")


def test_namespace_spec_missing_hierarchy_level():
    with pytest.raises(Exception):
        NamespaceSpec(
            version="0",
            hierarchy=["a", "b"],
            levels={"a": NamespaceLevelSpec(template="{a}", regex="(?P<a>.+)")},
        )


# ---------------------------------------------------------------------------
# Loading YAML spec files


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
def test_load_yaml_spec(version):
    path = _SPEC_DIR / f"namespace.{version}.yaml"
    assert path.exists(), f"Missing spec file: {path}"
    builder = NamespaceBuilder.from_yaml(path)
    assert builder.spec.version is not None
    assert len(builder.hierarchy) >= 2


def test_v3_hierarchy():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    assert b.hierarchy == ["subject", "acquisition", "session", "file"]
    assert b.optional_levels == []


def test_v2_optional_acquisition():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v2.yaml")
    assert "acquisition" in b.optional_levels


def test_v1_no_acquisition():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v1.yaml")
    assert "acquisition" not in b.hierarchy


# ---------------------------------------------------------------------------
# build_path


def test_build_subject():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    result = b.build_path("subject", VALUES_V3)
    assert result == "s082_tabfixed_m1099615_x"


def test_build_acquisition():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    result = b.build_path("acquisition", VALUES_V3)
    assert result == "s082_tabfixed_m1099615_x__20240502_131422__recording"


def test_build_unknown_level_raises():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    with pytest.raises(ValueError, match="Unknown level"):
        b.build_path("nonexistent", VALUES_V3)


def test_build_missing_field_raises():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    incomplete = {k: v for k, v in VALUES_V3.items() if k != "date"}
    with pytest.raises(ValueError, match="Missing value"):
        b.build_path("acquisition", incomplete)


# ---------------------------------------------------------------------------
# generate_path


def test_generate_path_to_file():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    path = b.generate_path("file", VALUES_V3)
    parts = path.split("/")
    assert len(parts) == 4
    assert parts[0] == "s082_tabfixed_m1099615_x"


def test_generate_path_to_subject_only():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    path = b.generate_path("subject", VALUES_V3)
    assert "/" not in path
    assert path == "s082_tabfixed_m1099615_x"


def test_generate_path_skip_optional():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v2.yaml")
    path = b.generate_path("session", VALUES_V3, include_optional_levels=False)
    parts = path.split("/")
    assert len(parts) == 2  # subject + session, no acquisition


# ---------------------------------------------------------------------------
# extract_level_values


def test_extract_subject_values():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    vals = b.extract_level_values("subject", "s082_tabfixed_m1099615_x")
    assert vals["subject_prefix"] == "s"
    assert vals["subject_id"] == "082"
    assert vals["mouse_id"] == "1099615"


def test_extract_unknown_level_raises():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    with pytest.raises(ValueError, match="Unknown level"):
        b.extract_level_values("bogus", "anything")


def test_extract_no_match_raises():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    with pytest.raises(ValueError, match="does not match"):
        b.extract_level_values("subject", "this_does_not_match_subject_regex")


# ---------------------------------------------------------------------------
# validate_path


def test_validate_path_stop_at_acquisition():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    from pathlib import Path as P

    full = (
        P("s082_tabfixed_m1099615_x")
        / "s082_tabfixed_m1099615_x__20240502_131422__recording"
        / "s082_tabfixed_m1099615_x__20240502_131422__recording__probabilistic_switching"
        / "s082_tabfixed_m1099615_x__20240502_131422__recording__probabilistic_switching.msw.pkl"
    )
    result = b.validate_path(full, stop_at="acquisition")
    assert result["date"] == "20240502"
    assert result["modality"] == "recording"


def test_validate_path_bad_stop_at_raises():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    with pytest.raises(ValueError, match="not in hierarchy"):
        b.validate_path("anything", stop_at="bogus")


# ---------------------------------------------------------------------------
# round-trip: to_dict → from_dict


def test_roundtrip_dict():
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    d = b.to_dict()
    b2 = NamespaceBuilder.from_dict(d)
    assert b2.hierarchy == b.hierarchy
    assert b2.spec.version == b.spec.version


# ---------------------------------------------------------------------------
# write_yaml round-trip


def test_write_and_reload_yaml(tmp_path):
    b = NamespaceBuilder.from_yaml(_SPEC_DIR / "namespace.v3.yaml")
    out = tmp_path / "out.yaml"
    b.write_yaml(out)
    b2 = NamespaceBuilder.from_yaml(out)
    assert b2.hierarchy == b.hierarchy
    assert b2.build_path("subject", VALUES_V3) == b.build_path("subject", VALUES_V3)
