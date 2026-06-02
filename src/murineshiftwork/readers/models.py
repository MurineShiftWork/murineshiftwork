"""MswSession — structured result of reading a single MSW session directory."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — pydantic validates Path fields at runtime
from typing import Any

import pandas as pd  # noqa: TC002 — pydantic validates pd.DataFrame at runtime
from pydantic import BaseModel, ConfigDict


class MswSession(BaseModel):
    """All data and metadata for one MSW session directory."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # identity
    session_dir: Path
    basename: str
    subject: str
    datetime_str: str
    task: str

    # provenance
    namespace_version: str | None
    artifact_format: str
    msw_version: str

    # content
    df: pd.DataFrame | None = None
    settings_task: dict[str, Any] | None = None
    settings_process: dict[str, Any] | None = None
    settings_stage: dict[str, Any] | None = None
    settings_ephys: dict[str, Any] | None = None

    # multi-protocol metadata (populated when session_manifest.yaml is present)
    subprotocols: list[dict] | None = None

    # flags
    is_complete: bool
    is_ephys: bool

    # acquisition context — set by load_acquisition(), absent for standalone sessions
    acquisition_name: str | None = None
    acquisition_dir: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_dir": str(self.session_dir),
            "basename": self.basename,
            "subject": self.subject,
            "datetime_str": self.datetime_str,
            "task": self.task,
            "namespace_version": self.namespace_version,
            "artifact_format": self.artifact_format,
            "msw_version": self.msw_version,
            "df": self.df,
            "settings_task": self.settings_task,
            "settings_process": self.settings_process,
            "settings_stage": self.settings_stage,
            "settings_ephys": self.settings_ephys,
            "subprotocols": self.subprotocols,
            "is_complete": self.is_complete,
            "is_ephys": self.is_ephys,
            "acquisition_name": self.acquisition_name,
            "acquisition_dir": str(self.acquisition_dir)
            if self.acquisition_dir
            else None,
        }
