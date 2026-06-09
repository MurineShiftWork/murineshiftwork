"""MSW session file naming — the .msw. artifact namespace.

Session-derived files follow the pattern defined in namespace.msw.yaml:
    {session_basename}.msw.{artifact}

The separator and pattern are defined declaratively in the YAML spec, not
hardcoded here. Use msw_file() for non-task callers; TaskRunner.get_path()
for task code that already has self available.
"""

from __future__ import annotations

from pathlib import Path


def msw_file(session_file_path: str | Path, artifact: str) -> Path:
    """Return the full Path for a session-derived .msw.{artifact} file.

    Args:
        session_file_path: Base session path (session_paths["session_file_path"]).
        artifact: Artifact name suffix (e.g. "session.yaml", "df.jsonl", "log").
    """
    from murineshiftwork.namespace.paths import get_msw_builder

    p = Path(session_file_path)
    b = get_msw_builder()
    values = b.extract_level_values("session", p.name)
    values["artifact"] = artifact
    return p.parent / b.build_path("file", values)


def is_msw_file(path: str | Path) -> bool:
    """Return True if the filename matches the MSW .msw. file pattern."""
    from murineshiftwork.namespace.paths import get_msw_builder

    try:
        get_msw_builder().extract_level_values("file", Path(path).name)
        return True
    except ValueError:
        return False


def msw_artifact(path: str | Path) -> str:
    """Extract the artifact suffix from an MSW filename.

    E.g. "subject__dt__task.msw.session.yaml" → "session.yaml"

    Raises:
        ValueError: If the path is not an MSW file.
    """
    from murineshiftwork.namespace.paths import get_msw_builder

    try:
        return get_msw_builder().extract_level_values("file", Path(path).name)[
            "artifact"
        ]
    except ValueError:
        raise ValueError(f"Not an MSW file: {path!r}")
