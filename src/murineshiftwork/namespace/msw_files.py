"""MSW session file naming — the .msw. namespace separator and artifact registry.

All session-derived files follow the pattern:
    {session_file_path}.msw.{artifact}

where {artifact} is one of the registered MSW_ARTIFACTS.  The separator
".msw." is the namespace marker; it identifies a file as belonging to a
specific session and produced by the MSW pipeline.

Usage:
    from murineshiftwork.namespace.msw_files import msw_file, MSW_ARTIFACTS

    path = msw_file(session_paths["session_file_path"], "session.yaml")
    # → Path("/data/subject/session/session.msw.session.yaml")

The most common artifacts are pre-built as keys in session_paths:
    session_paths["session_yaml"]   → msw_file(base, "session.yaml")
    session_paths["session_log"]    → msw_file(base, "log")
"""

from __future__ import annotations

from pathlib import Path

MSW_SEP = ".msw."

MSW_ARTIFACTS: frozenset[str] = frozenset(
    {
        "session.yaml",  # session metadata (process info, settings, trial counts)
        "plot_spec.yaml",  # copy of the task plot spec for this session
        "log",  # Python logging output
        "jsonl",  # trial data (one JSON object per line)
        "df.jsonl",  # trial dataframe export
        "df.pkl",  # trial dataframe (legacy pickle)
        "csv",  # pybpod raw CSV export
        "stimulation.json",  # stimulation metadata (optotagging, spindle, etc.)
    }
)


def msw_file(session_file_path: str | Path, artifact: str) -> Path:
    """Return the full Path for a session-derived .msw.{artifact} file.

    Args:
        session_file_path: Base session path (session_paths["session_file_path"]).
        artifact: One of the registered MSW_ARTIFACTS suffixes.

    Raises:
        ValueError: If artifact is not in MSW_ARTIFACTS.
    """
    if artifact not in MSW_ARTIFACTS:
        raise ValueError(
            f"Unknown MSW artifact {artifact!r}. Valid: {sorted(MSW_ARTIFACTS)}"
        )
    return Path(f"{session_file_path}{MSW_SEP}{artifact}")


def is_msw_file(path: str | Path) -> bool:
    """Return True if the filename contains the .msw. namespace separator."""
    return MSW_SEP in str(Path(path).name)


def msw_artifact(path: str | Path) -> str:
    """Extract the artifact suffix from an MSW filename.

    E.g. "subject__dt__task.msw.session.yaml" → "session.yaml"

    Raises:
        ValueError: If the path does not contain the .msw. separator.
    """
    name = str(Path(path).name)
    if MSW_SEP not in name:
        raise ValueError(f"Not an MSW file (no {MSW_SEP!r} segment): {name!r}")
    return name.split(MSW_SEP, 1)[1]
