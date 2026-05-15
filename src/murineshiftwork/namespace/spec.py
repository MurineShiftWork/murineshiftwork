"""Namespace spec: Pydantic models + YAML-backed NamespaceBuilder.

Replaces the configobj/INI-based NamespaceBuilder from the backup codebase.
Load a spec file:
    builder = NamespaceBuilder.from_yaml("namespace.msw.v3.yaml")
"""
from __future__ import annotations

import json
import logging
import os
import re
import string
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Pydantic models for the namespace spec

class NamespaceLevelSpec(BaseModel):
    template: str
    regex: str
    optional_fields: list[str] = []

    @field_validator("regex")
    @classmethod
    def _check_regex(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regex {v!r}: {exc}") from exc
        return v


class NamespaceSpec(BaseModel):
    version: str
    description: str = ""
    hierarchy: list[str]
    optional_levels: list[str] = []
    levels: dict[str, NamespaceLevelSpec]

    @field_validator("levels")
    @classmethod
    def _all_hierarchy_levels_present(
        cls, v: dict, info: Any
    ) -> dict:
        if "hierarchy" in (info.data or {}):
            missing = [h for h in info.data["hierarchy"] if h not in v]
            if missing:
                raise ValueError(
                    f"Hierarchy level(s) {missing} have no entry in 'levels'"
                )
        return v


# ---------------------------------------------------------------------------
# Helper

def _template_fields(template: str) -> list[str]:
    return [t[1] for t in string.Formatter().parse(template) if t[1]]


# ---------------------------------------------------------------------------
# NamespaceBuilder

class NamespaceBuilder:
    def __init__(self, spec: NamespaceSpec) -> None:
        self.spec = spec
        self.hierarchy: list[str] = spec.hierarchy
        self.optional_levels: list[str] = spec.optional_levels
        self._compiled: dict[str, re.Pattern] = {
            name: re.compile(level.regex)
            for name, level in spec.levels.items()
        }

    # ------------------------------------------------------------------
    # Construction

    @classmethod
    def from_yaml(cls, config_path: str | os.PathLike) -> "NamespaceBuilder":
        path = Path(config_path)
        with open(path) as f:
            data = yaml.safe_load(f)
        spec = NamespaceSpec.model_validate(data)
        logging.debug(f"Loaded NamespaceSpec v{spec.version} from {path}")
        return cls(spec)

    @classmethod
    def from_dict(cls, data: dict) -> "NamespaceBuilder":
        return cls(NamespaceSpec.model_validate(data))

    # ------------------------------------------------------------------
    # Serialisation

    def to_dict(self) -> dict:
        return self.spec.model_dump()

    def __str__(self) -> str:
        return f"NamespaceBuilder({json.dumps(self.to_dict())})"

    def __repr__(self) -> str:
        return f"NamespaceBuilder({self.to_dict()})"

    def write_yaml(self, path: str | os.PathLike) -> None:
        with open(path, "w") as f:
            yaml.dump(
                self.spec.model_dump(),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        logging.info(f"NamespaceSpec written to {path}")

    # ------------------------------------------------------------------
    # Path building

    def _build_one(self, level_name: str, values: dict, parts: dict) -> str:
        if level_name in parts:
            return parts[level_name]
        level = self.spec.levels[level_name]
        fields = _template_fields(level.template)
        for field in fields:
            if field in self.hierarchy and field not in parts:
                parts[field] = self._build_one(field, values, parts)
            elif field not in values and field not in parts:
                raise ValueError(
                    f"Missing value for field '{field}' in level '{level_name}'"
                )
        fmt = {k: parts.get(k, values.get(k, "")) for k in fields}
        result = level.template.format(**fmt)
        parts[level_name] = result
        return result

    def build_path(self, level: str, values: dict) -> str:
        """Build the path segment for *level* from *values*."""
        if level not in self.spec.levels:
            raise ValueError(f"Unknown level: {level!r}")
        return self._build_one(level, values, {})

    def generate_path(
        self,
        level: str,
        values: dict,
        include_optional_levels: bool = True,
    ) -> str:
        """Build the full path from root up to (and including) *level*."""
        if level not in self.hierarchy:
            raise ValueError(f"Unknown level: {level!r}")
        parts: dict[str, str] = {}
        segments: list[str] = []
        for name in self.hierarchy:
            if name in self.optional_levels and not include_optional_levels:
                continue
            segments.append(self._build_one(name, values, parts))
            if name == level:
                break
        return os.path.join(*segments)

    # ------------------------------------------------------------------
    # Parsing / validation

    def _match_level(
        self, level_name: str, segment: str, known_values: dict
    ) -> dict[str, str]:
        """Match *segment* against the compiled regex for *level_name*,
        with already-known parent values substituted into the pattern."""
        level = self.spec.levels[level_name]
        pattern = level.regex
        for k, v in known_values.items():
            if v is not None:
                pattern = pattern.replace("{" + k + "}", re.escape(str(v)))
        m = re.match(pattern, segment.strip())
        if not m:
            raise ValueError(
                f"Segment {segment!r} did not match regex for level {level_name!r}"
            )
        return m.groupdict()

    def validate_path_level(
        self, level: str, segment: str, known_values: dict
    ) -> dict[str, str]:
        return self._match_level(level, segment, known_values)

    def validate_path(
        self, path: str | os.PathLike, stop_at: str | None = None
    ) -> dict[str, str]:
        if stop_at and stop_at not in self.hierarchy:
            raise ValueError(f"stop_at level {stop_at!r} is not in hierarchy")
        max_depth = (
            self.hierarchy.index(stop_at) + 1
            if stop_at
            else len(self.hierarchy)
        )
        segments = Path(path).parts
        result: dict[str, str] = {}
        for i, (segment, level_name) in enumerate(
            zip(segments, self.hierarchy)
        ):
            if i >= max_depth:
                break
            result.update(self._match_level(level_name, segment, result))
            if level_name == stop_at:
                break
        return result

    def extract_level_values(self, level: str, name: str) -> dict[str, str]:
        if level not in self.hierarchy:
            raise ValueError(f"Unknown level: {level!r}")
        match = self._compiled[level].match(name.strip())
        if not match:
            raise ValueError(
                f"Name {name!r} does not match regex for level {level!r}"
            )
        fields = _template_fields(self.spec.levels[level].template)
        return {f: match.groupdict().get(f, "") for f in fields}
