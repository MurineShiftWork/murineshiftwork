"""
murineshiftwork.readers.validate
------------------------------------
Post-session validation: MSW file completeness.

Validates that the required MSW artifacts (df, settings.task, settings.process)
are present and loadable. Camera/RCE file checks belong in rpi_camera_ensemble;
call rce.validate_session(session_dir) there after MSW validation.

Usage
-----
    from murineshiftwork.readers.validate import validate_session

    result = validate_session("/data/subject/session_dir")
    result.print_summary()
    print(result.passed)   # True / False
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from murineshiftwork.readers.session import read_session_data

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    session_dir: Path
    msw_version: str = "unknown"

    passed: bool = True
    issues: list[str] = field(default_factory=list)  # blocking failures
    warnings: list[str] = field(default_factory=list)  # non-blocking concerns
    info: list[str] = field(default_factory=list)  # informational

    def _fail(self, msg: str) -> None:
        self.passed = False
        self.issues.append(msg)

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def _info(self, msg: str) -> None:
        self.info.append(msg)

    def print_summary(self) -> None:
        status = "PASS" if self.passed else "FAIL"
        print(f"\n{'=' * 60}")
        print(f"Session validation: {status}")
        print(f"  dir        : {self.session_dir.name}")
        print(f"  msw_version: {self.msw_version}")

        for msg in self.info:
            print(f"  INFO  : {msg}")
        for msg in self.warnings:
            print(f"  WARN  : {msg}")
        for msg in self.issues:
            print(f"  FAIL  : {msg}")
        print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# MSW file completeness
# ---------------------------------------------------------------------------


def _check_msw_completeness(session_dir: Path, result: ValidationResult) -> dict | None:
    try:
        sd = read_session_data(session_dir=session_dir)
    except Exception as e:
        result._fail(f"read_session_data() raised: {e}")
        return None

    result.msw_version = sd.get("msw_version", "unknown")

    if not sd.get("is_complete_session", False):
        missing = [
            k
            for k in ("df", "settings.task", "settings.process")
            if k not in sd or sd[k] is None
        ]
        result._fail(f"Incomplete MSW session — missing or null: {missing}")
    else:
        result._info(f"MSW files complete (version={result.msw_version})")

    if sd.get("is_legacy_session"):
        result._info("Legacy session format detected")

    return sd


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def validate_session(
    session_dir: str | Path,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate MSW file completeness for a session directory.

    Parameters
    ----------
    session_dir:
        Path to the session directory.
    verbose:
        If True, print summary to stdout after validation.

    Returns
    -------
    ValidationResult
        .passed   — True if no blocking issues
        .issues   — list of failure strings
        .warnings — list of non-blocking strings
    """
    session_dir = Path(session_dir)
    result = ValidationResult(session_dir=session_dir)

    _check_msw_completeness(session_dir, result)

    if verbose:
        result.print_summary()

    return result
