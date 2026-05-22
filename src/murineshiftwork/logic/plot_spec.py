from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator

VALID_PANEL_TYPES = frozenset(
    {"rolling_mean", "timeseries", "cumulative_sum", "histogram", "raster", "scatter"}
)

_REQUIRED_FIELDS: dict[str, set[str]] = {
    "rolling_mean": {"x", "value"},
    "timeseries": {"x", "value"},
    "cumulative_sum": {"x", "value"},
    "histogram": {"value"},
    "raster": {"x", "times"},
    "scatter": {"x", "y"},
}


class PanelSpec(BaseModel):
    id: str
    title: str
    type: str
    fields: dict[str, str]
    options: dict[str, Any] = {}

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in VALID_PANEL_TYPES:
            raise ValueError(
                f"Unknown panel type '{v}'. Valid: {sorted(VALID_PANEL_TYPES)}"
            )
        return v

    @model_validator(mode="after")
    def _required_fields_present(self) -> "PanelSpec":
        required = _REQUIRED_FIELDS.get(self.type, set())
        missing = required - set(self.fields)
        if missing:
            raise ValueError(
                f"Panel '{self.id}' (type={self.type}) missing fields: {missing}"
            )
        return self


class PlotSpec(BaseModel):
    version: int
    task: str
    panels: list[PanelSpec]

    @field_validator("version")
    @classmethod
    def _valid_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError(f"Unsupported plot_spec version {v} (expected 1)")
        return v

    @field_validator("panels")
    @classmethod
    def _unique_ids(cls, panels: list[PanelSpec]) -> list[PanelSpec]:
        seen: set[str] = set()
        for p in panels:
            if p.id in seen:
                raise ValueError(f"Duplicate panel id '{p.id}'")
            seen.add(p.id)
        return panels

    def panel(self, panel_id: str) -> PanelSpec:
        """Return panel by id; raise KeyError if not found."""
        for p in self.panels:
            if p.id == panel_id:
                return p
        raise KeyError(f"No panel with id '{panel_id}' in spec for task '{self.task}'")

    @classmethod
    def from_yaml(cls, path: Path | str) -> "PlotSpec":
        data = yaml.safe_load(Path(path).read_text())
        return cls.model_validate(data)
