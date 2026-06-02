"""Tests for PlotSpec YAML schema loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from murineshiftwork.logagent.plot_spec import VALID_PANEL_TYPES, PanelSpec, PlotSpec

TASKS_DIR = Path(__file__).parent.parent / "src/murineshiftwork/tasks"


def _find_plot_specs() -> list[Path]:
    return sorted(TASKS_DIR.glob("*/plot_spec.yaml"))


# ---------------------------------------------------------------------------
# Schema unit tests


def test_panel_valid_type():
    p = PanelSpec(id="x", title="X", type="timeseries", fields={"x": "a", "value": "b"})
    assert p.type == "timeseries"


def test_panel_rejects_unknown_type():
    with pytest.raises(Exception, match="Unknown panel type"):
        PanelSpec(id="x", title="X", type="foobar", fields={"x": "a"})


@pytest.mark.parametrize(
    "ptype, fields",
    [
        ("rolling_mean", {"x": "t"}),
        ("timeseries", {"x": "t"}),
        ("cumulative_sum", {"x": "t"}),
        ("raster", {"x": "t"}),
        ("scatter", {"x": "a"}),
    ],
)
def test_panel_missing_required_field(ptype, fields):
    with pytest.raises(Exception):
        PanelSpec(id="x", title="X", type=ptype, fields=fields)


def test_plot_spec_duplicate_ids_rejected():
    panel = {
        "id": "dup",
        "title": "Dup",
        "type": "timeseries",
        "fields": {"x": "a", "value": "b"},
    }
    with pytest.raises(Exception, match="Duplicate panel id"):
        PlotSpec(version=1, task="test", panels=[panel, panel])


def test_plot_spec_wrong_version():
    with pytest.raises(Exception, match="version"):
        PlotSpec(version=2, task="test", panels=[])


# ---------------------------------------------------------------------------
# File-based tests


@pytest.mark.parametrize("spec_path", _find_plot_specs(), ids=lambda p: p.parent.name)
def test_plot_spec_yaml_loads(spec_path: Path):
    spec = PlotSpec.from_yaml(spec_path)
    assert spec.version == 1
    assert spec.task
    assert len(spec.panels) > 0


@pytest.mark.parametrize("spec_path", _find_plot_specs(), ids=lambda p: p.parent.name)
def test_plot_spec_panel_types_valid(spec_path: Path):
    spec = PlotSpec.from_yaml(spec_path)
    for panel in spec.panels:
        assert panel.type in VALID_PANEL_TYPES
        assert panel.id
        assert panel.title


@pytest.mark.parametrize("spec_path", _find_plot_specs(), ids=lambda p: p.parent.name)
def test_plot_spec_panel_ids_unique(spec_path: Path):
    spec = PlotSpec.from_yaml(spec_path)
    ids = [p.id for p in spec.panels]
    assert len(ids) == len(set(ids)), f"Duplicate panel ids in {spec_path}"


def test_plot_spec_panel_lookup():
    spec = PlotSpec.from_yaml(TASKS_DIR / "sequence/plot_spec.yaml")
    panel = spec.panel("outcomes_perf")
    assert panel.type == "rolling_mean"
    assert "value" in panel.fields

    with pytest.raises(KeyError):
        spec.panel("nonexistent_panel")


def test_sequence_plot_spec_has_expected_panels():
    spec = PlotSpec.from_yaml(TASKS_DIR / "sequence/plot_spec.yaml")
    assert spec.task == "sequence"
    panel_ids = {p.id for p in spec.panels}
    assert "outcomes_perf" in panel_ids
    assert "training_level" in panel_ids
    assert "session_progress" in panel_ids
    assert "poke_raster" in panel_ids
