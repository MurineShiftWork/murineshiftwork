from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Namespace versions
#
# A namespace version defines the datetime format used in session basenames.
# The session basename structure is always:
#   {subject}__{datetime}__{task}
#
# Version is passed explicitly to generate_session_paths() so the caller
# (core logic / CLI) controls which namespace is written.  parse_session_basename()
# identifies the version of any existing basename from the datetime field width.

NAMESPACE_V1 = "v1"        # current: microsecond precision  e.g. 20260514_143022_123456
NAMESPACE_LEGACY = "legacy" # pre-v1:  second precision       e.g. 20210718_152153

CURRENT_NAMESPACE_VERSION = NAMESPACE_V1

_NAMESPACE_FORMATS: dict[str, str] = {
    NAMESPACE_V1:     "%Y%m%d_%H%M%S_%f",
    NAMESPACE_LEGACY: "%Y%m%d_%H%M%S",
}

# Parse order: most-specific first so the longer microsecond format is tried before
# the seconds format (which is a valid prefix of the microsecond string).
_PARSE_ORDER = [NAMESPACE_V1, NAMESPACE_LEGACY]

# ---------------------------------------------------------------------------
# Path validation

# Characters forbidden in subject / task path components.
_FORBIDDEN_PATH_CHARS = re.compile(r'[#@!$%^&*()+=\[\]{};:\'",<>?\\|`~ ]')

# Convenience alias used by logic/paths.py shim
MSW_DATETIME_FORMAT = _NAMESPACE_FORMATS[CURRENT_NAMESPACE_VERSION]


def _validate_path_component(value: str, field: str) -> None:
    if _FORBIDDEN_PATH_CHARS.search(value):
        bad = _FORBIDDEN_PATH_CHARS.findall(value)
        raise ValueError(
            f"{field} contains forbidden characters {bad!r}: {value!r}. "
            "Use only letters, digits, hyphens, and underscores."
        )


# ---------------------------------------------------------------------------
# Generation

def generate_session_paths(
    subject: str,
    task: str,
    basepath: str | Path,
    version: str = CURRENT_NAMESPACE_VERSION,
    default_subject: str = "_test_subject",
    is_child_session_to: str | None = None,
    printout: bool = True,
) -> dict:
    """Generate validated session path dict for a given namespace version.

    Parameters
    ----------
    subject:            Subject name (validated against forbidden chars).
    task:               Task name.
    basepath:           Root output directory.
    version:            Namespace version — one of NAMESPACE_V1, NAMESPACE_LEGACY.
                        Controls the datetime format written into the session basename.
    default_subject:    Fallback subject name used when *task* starts with '_test__'.
    is_child_session_to: If set, the session folder is nested inside this parent basename.
    printout:           Print the path table to stdout.

    Returns
    -------
    dict with keys: subject, datetime, task, basepath, namespace_version,
    session_basename, session_basename_behav, session_folder, session_file_path.
    """
    if version not in _NAMESPACE_FORMATS:
        raise ValueError(
            f"Unknown namespace version {version!r}. "
            f"Choose from: {list(_NAMESPACE_FORMATS)}"
        )

    basepath = Path(basepath)

    if str(task).startswith("_test__"):
        subject = default_subject
    _validate_path_component(subject, "Subject name")

    dt = datetime.now().strftime(_NAMESPACE_FORMATS[version])
    session_basename = "__".join([subject, dt, task])

    if is_child_session_to:
        session_folder = basepath / subject / is_child_session_to / session_basename
    else:
        session_folder = basepath / subject / session_basename

    session_paths = {
        "subject": subject,
        "datetime": dt,
        "task": task,
        "basepath": basepath,
        "namespace_version": version,
        "session_basename": session_basename,
        "session_basename_behav": session_basename + ".msw",
        "session_folder": str(session_folder),
        "session_file_path": str(session_folder / session_basename),
    }

    if printout:
        print("\n   Session paths: \n")
        for k, v in session_paths.items():
            print(f"{k:>30}:{'':>2}{v}")
        print("\n")

    return session_paths


# ---------------------------------------------------------------------------
# Compatibility shim — existing callers use build_data_paths

def build_data_paths(
    basepath=None,
    subject=None,
    task=None,
    default_subject="_test_subject",
    is_child_session_to=None,
    printout=True,
):
    """Compatibility shim — calls generate_session_paths with CURRENT_NAMESPACE_VERSION."""
    return generate_session_paths(
        subject=subject,
        task=task,
        basepath=basepath,
        version=CURRENT_NAMESPACE_VERSION,
        default_subject=default_subject,
        is_child_session_to=is_child_session_to,
        printout=printout,
    )


# ---------------------------------------------------------------------------
# Parsing

def parse_session_basename(basename: str) -> dict:
    """Parse subject, datetime, task from a session basename.

    Identifies the namespace version from the datetime field width and format.

    Returns dict with keys:
        subject (str), datetime (datetime), datetime_str (str),
        task (str), namespace_version (str).

    Raises ValueError if the basename cannot be parsed.
    """
    parts = str(basename).split("__")
    if len(parts) != 3:
        raise ValueError(
            f"Expected 3 '__'-separated parts (subject, datetime, task), "
            f"got {len(parts)} in: {basename!r}"
        )
    subject, dt_str, task = parts

    for version in _PARSE_ORDER:
        try:
            dt = datetime.strptime(dt_str, _NAMESPACE_FORMATS[version])
            return {
                "subject": subject,
                "datetime": dt,
                "datetime_str": dt_str,
                "task": task,
                "namespace_version": version,
            }
        except ValueError:
            continue

    raise ValueError(
        f"Cannot parse datetime {dt_str!r} in basename {basename!r}. "
        f"Tried namespace versions: {_PARSE_ORDER}"
    )
