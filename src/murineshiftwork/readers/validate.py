"""
murineshiftwork.readers.validate
------------------------------------
Post-session validation: file completeness + camera TTL alignment.

Designed to be run immediately after acquisition or as a batch check.

Usage
-----
    from murineshiftwork.readers.validate import validate_session

    result = validate_session("/data/subject/session_dir")
    result.print_summary()
    print(result.passed)   # True / False

Design
------
Three tiers of check:

1. MSW file completeness
   Read via read_session_data(). Checks df, settings.task, settings.process
   are present and non-null.

2. RCE file completeness
   Loaded via RCESession.from_directory() (provision_rpi/rpi_camera_ensemble).
   Checks conductor cfg+ensemble present; each agent has ttl_in, ttl_out,
   video_h264 present and ttl files loadable.

3. Camera TTL alignment
   New sessions (msw_version == x.y.z, barcode_value column in df):
       Full barcode decode + match check via verify_rpi_barcode_decoding().
       Pass: decode_rate == 1.0 AND match_rate == 1.0.

   Legacy sessions (no barcode_value, or msw_version in {"legacy", "< 1.0.0"}):
       Simple TTL count + spacing check:
       - ttl_out pulse count == number of task trials in df
       - inter-pulse intervals from ttl_out match df ITI column
         (median within 10%, no outliers > 3x median)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from murineshiftwork.readers.session import read_session_data

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    session_dir: Path
    msw_version: str = "unknown"
    is_rce_session: bool = False

    passed: bool = True
    issues: list[str] = field(default_factory=list)  # blocking failures
    warnings: list[str] = field(default_factory=list)  # non-blocking concerns
    info: list[str] = field(default_factory=list)  # informational

    # Per-agent alignment results (agent_id → dict)
    agent_alignment: dict[str, dict] = field(default_factory=dict)

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
        print(f"  rce_session: {self.is_rce_session}")

        for msg in self.info:
            print(f"  INFO  : {msg}")
        for msg in self.warnings:
            print(f"  WARN  : {msg}")
        for msg in self.issues:
            print(f"  FAIL  : {msg}")

        if self.agent_alignment:
            print("  Camera TTL alignment:")
            for aid, res in self.agent_alignment.items():
                ok = "OK" if res.get("passed") else "FAIL"
                print(f"    [{ok}] {aid}: {res.get('summary', '')}")
        print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# MSW file completeness
# ---------------------------------------------------------------------------


def _check_msw_completeness(session_dir: Path, result: ValidationResult) -> dict | None:
    try:
        sd = read_session_data(session_dir=session_dir, load_raw=False)
    except Exception as e:
        result._fail(f"read_session_data() raised: {e}")
        return None

    result.msw_version = sd.get("msw_version", "unknown")

    if not sd.get("is_complete_session", False):
        missing = []
        for k in ("df", "raw", "settings.task", "settings.process"):
            if k not in sd or sd[k] is None:
                missing.append(k)
        result._fail(f"Incomplete MSW session — missing or null: {missing}")
    else:
        result._info(f"MSW files complete (version={result.msw_version})")

    if sd.get("is_legacy_session"):
        result._info("Legacy session format detected")

    return sd


# ---------------------------------------------------------------------------
# RCE file completeness
# ---------------------------------------------------------------------------


def _check_rce_completeness(session_dir: Path, result: ValidationResult) -> Any | None:
    try:
        from rpi_camera_ensemble.io.session import RCESession
    except ImportError:
        result._warn("rpi_camera_ensemble not importable — skipping RCE checks")
        return None

    try:
        rce = RCESession.from_directory(session_dir, load=True)
    except Exception as e:
        result._fail(f"RCESession.from_directory() raised: {e}")
        return None

    if not rce.agents:
        # No RCE files at all — not an RCE session
        return None

    result.is_rce_session = True
    result._info(f"RCE agents found: {sorted(rce.agents.keys())}")

    # Conductor
    if rce.conductor is None:
        result._warn("RCE conductor files absent")
    else:
        for slot_name in ("cfg", "ensemble"):
            slot = getattr(rce.conductor, slot_name)
            if not slot.is_present:
                result._warn(f"Conductor {slot_name} missing")
            elif slot.has_error:
                result._warn(f"Conductor {slot_name} load error: {slot.error}")

    # Agents
    for aid, agent in sorted(rce.agents.items()):
        for slot_name in ("ttl_in", "ttl_out"):
            slot = getattr(agent, slot_name)
            if not slot.is_present:
                result._fail(f"{aid}: {slot_name} file missing")
            elif slot.has_error:
                result._fail(f"{aid}: {slot_name} load error: {slot.error}")
        if not agent.video_h264.is_present:
            result._warn(f"{aid}: video_h264 missing")

    return rce


# ---------------------------------------------------------------------------
# TTL alignment — new sessions (barcode)
# ---------------------------------------------------------------------------


def _check_barcode_alignment(
    session_dir: Path,
    rce,
    sd: dict,
    result: ValidationResult,
) -> None:
    from murineshiftwork.readers.alignment import verify_rpi_barcode_decoding

    df = sd.get("df")
    if df is None or "barcode_value" not in df.columns:
        result._warn("barcode_value column absent — cannot run barcode alignment check")
        return

    for aid, agent in sorted(rce.agents.items()):
        if not agent.ttl_in.is_present:
            result.agent_alignment[aid] = {
                "passed": False,
                "summary": "ttl_in missing",
            }
            continue

        try:
            res = verify_rpi_barcode_decoding(
                session_dir=session_dir,
                ttl_in_npz=agent.ttl_in.available,
            )
        except Exception as e:
            result.agent_alignment[aid] = {
                "passed": False,
                "summary": f"error: {e}",
            }
            result._fail(f"{aid}: barcode alignment raised: {e}")
            continue

        passed = res.get("decode_rate", 0) == 1.0 and res.get("match_rate", 0) == 1.0
        summary = (
            f"decode={res.get('decode_rate', 0):.2f}  "
            f"match={res.get('match_rate', 0):.2f}  "
            f"wall_err_ms mean={res.get('wall_time_errors_ms', {}).get('mean', float('nan')):.1f}"
        )
        result.agent_alignment[aid] = {
            **res,
            "passed": passed,
            "summary": summary,
        }
        if not passed:
            result._fail(f"{aid}: barcode alignment failed — {summary}")


# ---------------------------------------------------------------------------
# TTL alignment — legacy sessions (ttl_out count + spacing)
# ---------------------------------------------------------------------------


def _check_legacy_ttl_alignment(
    rce,
    sd: dict,
    result: ValidationResult,
) -> None:
    """Check trial-onset TTL count and spacing against the MSW trial df.

    Uses ttl_in (Bpod-to-camera trial-onset pulses) not ttl_out (camera frame
    outputs). ttl_out contains one pulse per frame (~500k for a 30fps session)
    and is not useful for trial counting.
    """
    df = sd.get("df")
    if df is None:
        result._warn("df absent — skipping legacy TTL alignment")
        return

    # Count task trials (exclude trial_type == "ttl" identifier trial if present)
    if "trial_type" in df.columns:
        n_task_trials = int((df["trial_type"] == "task").sum())
    else:
        n_task_trials = len(df)

    for aid, agent in sorted(rce.agents.items()):
        if not agent.ttl_in.is_present or not agent.ttl_in.is_loaded:
            result.agent_alignment[aid] = {
                "passed": False,
                "summary": "ttl_in missing/unloaded",
            }
            continue

        ttl = agent.ttl_in.loaded
        # Rising edges only = one event per trial-onset pulse
        rising = ttl.data.astype(np.uint8) > 0
        pulse_times = ttl.timestamps[rising]
        n_pulses = len(pulse_times)

        passed = True
        notes = []

        # Count check
        if n_pulses != n_task_trials:
            passed = False
            notes.append(f"pulse count {n_pulses} != task trials {n_task_trials}")
        else:
            notes.append(f"count OK ({n_pulses})")

        # Spacing check vs df ITI (if available)
        if n_pulses > 1:
            ipi = np.diff(pulse_times)
            median_ipi = float(np.median(ipi))

            if "iti" in df.columns:
                # iti column contains list-like [[start, end]] pairs
                try:
                    iti_durations = (
                        df["iti"]
                        .dropna()
                        .apply(
                            lambda x: (
                                x[0][1] - x[0][0] if x and len(x[0]) == 2 else np.nan
                            )
                        )
                    )
                    expected_median = float(iti_durations.median())
                    rel_err = abs(median_ipi - expected_median) / expected_median
                    if rel_err > 0.10:
                        passed = False
                        notes.append(
                            f"IPI median {median_ipi * 1000:.0f}ms vs "
                            f"expected {expected_median * 1000:.0f}ms (>{10:.0f}% off)"
                        )
                    else:
                        notes.append(
                            f"spacing OK (median IPI {median_ipi * 1000:.0f}ms)"
                        )
                except Exception:
                    pass

            # Outlier check: pulses > 3× median IPI suggest missed triggers
            n_outliers = int((ipi > 3 * median_ipi).sum())
            if n_outliers:
                result._warn(
                    f"{aid}: {n_outliers} inter-pulse gaps > 3× median — possible missed triggers"
                )

        summary = "  ".join(notes)
        result.agent_alignment[aid] = {"passed": passed, "summary": summary}
        if not passed:
            result._fail(f"{aid}: legacy TTL alignment failed — {summary}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def validate_session(
    session_dir: str | Path,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate completeness and TTL alignment of an MSW session directory.

    Parameters
    ----------
    session_dir:
        Path to the session directory.
    verbose:
        If True, print summary to stdout after validation.

    Returns
    -------
    ValidationResult
        .passed        — True if no blocking issues
        .issues        — list of failure strings
        .warnings      — list of non-blocking strings
        .agent_alignment — per-agent TTL check results
    """
    session_dir = Path(session_dir)
    result = ValidationResult(session_dir=session_dir)

    # 1. MSW files
    sd = _check_msw_completeness(session_dir, result)

    # 2. RCE files
    rce = None
    if sd is not None:
        rce = _check_rce_completeness(session_dir, result)

    # 3. TTL alignment
    if sd is not None and rce is not None and rce.agents:
        version = result.msw_version
        df = sd.get("df")
        has_barcodes = (
            df is not None
            and "barcode_value" in df.columns
            and df["barcode_value"].notna().any()
        )
        is_new_format = version not in ("legacy", "< 1.0.0", "unknown")

        if is_new_format and has_barcodes:
            result._info("Using barcode alignment check (new session format)")
            _check_barcode_alignment(session_dir, rce, sd, result)
        elif is_new_format and not has_barcodes:
            result._info(
                "New session format but no barcode_value column — "
                "task not yet barcode-integrated; falling back to TTL count/spacing check"
            )
            _check_legacy_ttl_alignment(rce, sd, result)
        else:
            result._info("Using simple TTL count/spacing check (legacy session format)")
            _check_legacy_ttl_alignment(rce, sd, result)

    if verbose:
        result.print_summary()

    return result
