import logging
from pathlib import Path

from murineshiftwork.namespace.msw_files import is_msw_file

# ---------------------------------------------------------------------------
# Artifact format constants
#
# Two orthogonal dimensions describe every session on disk:
#   1. namespace_version — basename datetime format (NAMESPACE_LEGACY / NAMESPACE_V1)
#   2. artifact_format   — how settings/process/task data is stored (constants below)
#
# These are independent: fixture_jsonl uses NAMESPACE_V1 basenames but
# ARTIFACT_FORMAT_SEPARATE_JSON settings files (before the unified YAML was introduced).

ARTIFACT_FORMAT_LEGACY = "legacy"
# Pre-.msw. era: task_settings.py + switching.pkl/csv

ARTIFACT_FORMAT_SEPARATE_JSON = "separate_json"
# Two separate .msw.settings.process.json + .msw.settings.task.json files,
# plus .msw.df.pkl or .msw.df.jsonl

ARTIFACT_FORMAT_SESSION_YAML = "session_yaml"
# Single .msw.session.yaml (msw_format_version: 2+) with unified process + task_settings


# ---------------------------------------------------------------------------
# Legacy detection helpers (used by session.py — kept for backward compat)


def test_is_legacy_msw_file(file):
    """Test if file is legacy namespace file."""
    file = str(file)
    return (
        Path(file).name.endswith("switching.pkl")
        or Path(file).name.endswith("switching.csv")
        or Path(file).name.endswith("task_settings.py")
    )


def test_is_recognized_msw_file(file):
    """Test if file is current or legacy namespace file."""
    file = str(file)
    # Back-compat: sequence task previously wrote *.df.jsonl without .msw. segment
    if file.endswith(".df.jsonl") and not is_msw_file(file):
        return True
    return is_msw_file(file) or test_is_legacy_msw_file(file=file)


def test_is_legacy_format(session_dir=None):
    """Test if files in session folder are legacy namespace file."""
    session_dir = Path(session_dir)
    assert session_dir.exists()

    session_files = [str(p) for p in session_dir.glob("*")]

    for f in session_files:
        if test_is_legacy_msw_file(file=f):
            logging.debug(
                f"Is legacy MSW data format (identified on file: '{Path(f).name}'): {str(session_dir)}"
            )
            return True

    return False


# ---------------------------------------------------------------------------
# Format detection (retrograde reader framework)


def _infer_session_basename(session_dir: Path) -> str | None:
    """Extract session basename from .msw. filenames in directory.

    Works for both real sessions (where dir name IS the basename) and test
    fixtures (where the dir has a generic name like 'fixture_pkl').
    """
    for f in session_dir.iterdir():
        if ".msw." in f.name:
            return f.name.split(".msw.")[0]
    return None


def detect_artifact_format(session_dir: Path) -> str:
    """Detect artifact storage format from files present in *session_dir*.

    Returns one of ARTIFACT_FORMAT_LEGACY, ARTIFACT_FORMAT_SEPARATE_JSON,
    or ARTIFACT_FORMAT_SESSION_YAML.
    """
    session_dir = Path(session_dir)
    names = {p.name for p in session_dir.iterdir()}

    if any(
        n.endswith("task_settings.py")
        or n.endswith("switching.pkl")
        or n.endswith("switching.csv")
        for n in names
    ):
        return ARTIFACT_FORMAT_LEGACY

    if any(".msw.session.yaml" in n for n in names):
        return ARTIFACT_FORMAT_SESSION_YAML

    if any(".msw.settings.process.json" in n for n in names):
        return ARTIFACT_FORMAT_SEPARATE_JSON

    return ARTIFACT_FORMAT_LEGACY


def detect_session_format(session_dir: Path) -> dict:
    """Detect namespace version and artifact format for a session directory.

    Parameters
    ----------
    session_dir : Path
        Directory containing session files.  Can be a real session dir (name
        equals basename) or a test fixture dir with a generic name.

    Returns
    -------
    dict with keys:
        basename (str)         — inferred or directory name
        namespace_version (str | None) — NAMESPACE_V1, NAMESPACE_LEGACY, or None
        artifact_format (str)  — one of the ARTIFACT_FORMAT_* constants
        parse_error (str | None) — set when basename cannot be parsed
    """
    from murineshiftwork.namespace.paths import parse_session_basename

    session_dir = Path(session_dir)
    artifact_format = detect_artifact_format(session_dir)

    basename = _infer_session_basename(session_dir) or session_dir.name

    try:
        info = parse_session_basename(basename)
        namespace_version = info["namespace_version"]
        parse_error = None
    except ValueError as exc:
        namespace_version = None
        parse_error = str(exc)

    return {
        "basename": basename,
        "namespace_version": namespace_version,
        "artifact_format": artifact_format,
        "parse_error": parse_error,
    }


def validate_session_namespace(session_dir: Path) -> dict:
    """Validate that the session basename conforms to the MSW namespace spec.

    Uses the NamespaceBuilder regex to confirm the basename can be fully
    parsed (subject, datetime, task fields all present and well-formed).

    Parameters
    ----------
    session_dir : Path
        Directory containing session files.

    Returns
    -------
    dict with keys:
        valid (bool)
        namespace_version (str | None)
        basename (str)
        error (str | None)
    """
    from murineshiftwork.namespace.paths import parse_session_basename

    session_dir = Path(session_dir)
    basename = _infer_session_basename(session_dir) or session_dir.name

    try:
        info = parse_session_basename(basename)
        return {
            "valid": True,
            "namespace_version": info["namespace_version"],
            "basename": basename,
            "error": None,
        }
    except ValueError as exc:
        return {
            "valid": False,
            "namespace_version": None,
            "basename": basename,
            "error": str(exc),
        }
