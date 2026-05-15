"""
Ephys alignment for MSW sessions using TTL barcode events.
Also includes rpi_camera_ensemble TTL-in verification for testing barcode decodability.

Usage
-----
from murineshiftwork.readers.alignment import align_session_to_ephys, verify_rpi_barcode_decoding

# ephys_events is a DataFrame from open-ephys-python-tools, e.g.:
#   session.recordnodes[0].recordings[0].events
# with columns: line, state, timestamps (and optionally corrected_timestamps)

df, result = align_session_to_ephys(
    session_dir="/data/.../session_dir",
    ephys_events=ephys_events,
    barcode_bnc_line=2,               # ephys digital line wired to HARDWARE_BNC_BARCODE
    timestamp_column="timestamps",    # or "corrected_timestamps" if processor alignment was run
)

# Convert any bpod-clock time to ephys time:
ephys_t = result["bpod_to_ephys"](bpod_t)

# The returned df has extra columns:
#   trial_start_ephys   - ephys-aligned trial start for every trial
#   barcode_ephys_time  - matched ephys time for each barcode (NaN for non-barcode trials)
#   alignment_slope, alignment_intercept, n_barcodes_matched
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from ttl_barcoder.core.barcode_ttl import BarcodeTTL
from ttl_barcoder.core.config import BarcodeConfig

from murineshiftwork.logic.barcode import BARCODE_FIRST_STATE_NAME
from murineshiftwork.readers.session import read_session_data

# Minimum gap between edges that signals a new barcode (seconds).
# Within a barcode, max gap = bit_duration (~35ms). Between barcodes the
# gap is at least the pre-barcode ITI portion, typically >> 500ms.
_INTER_BARCODE_GAP_S = 0.5


def decode_ephys_barcodes(
    ephys_events: pd.DataFrame,
    barcode_bnc_line: int,
    timestamp_column: str = "timestamps",
    barcode_config: Optional[BarcodeConfig] = None,
) -> list[tuple[float, int]]:
    """Decode barcode events from an open-ephys-python-tools events DataFrame.

    Args:
        ephys_events:     Events df with columns: line, state, <timestamp_column>.
                          state=1 rising (HIGH), state=0 falling (LOW).
        barcode_bnc_line: Digital line number wired to the barcode BNC output.
        timestamp_column: Which timestamp column to use. "timestamps" for raw ephys
                          clock; "corrected_timestamps" if global processor alignment
                          was applied (preferred for multi-processor recordings).
        barcode_config:   Must match the config used during acquisition. Defaults to
                          BarcodeConfig.default() (37-bit, 35ms bits, 10ms init).

    Returns:
        List of (ephys_time, barcode_value) tuples, one per successfully decoded barcode.
        ephys_time is the timestamp of the first edge of that barcode.
    """
    if barcode_config is None:
        barcode_config = BarcodeConfig.default()

    barcoder = BarcodeTTL(barcode_config)

    line_df = (
        ephys_events[ephys_events["line"] == barcode_bnc_line]
        .sort_values(timestamp_column)
        .reset_index(drop=True)
    )

    if line_df.empty:
        logging.warning(f"No events found on ephys line {barcode_bnc_line}.")
        return []

    edge_times = line_df[timestamp_column].values
    edge_levels = line_df["state"].values.astype(bool)

    # Split edge stream into individual barcode packets on long gaps
    gap_indices = np.where(np.diff(edge_times) > _INTER_BARCODE_GAP_S)[0] + 1
    segments = np.split(np.arange(len(edge_times)), gap_indices)

    results = []
    for seg_idx in segments:
        if len(seg_idx) < 6:
            continue
        decoded = barcoder.decode_edges(
            edge_timestamps=list(edge_times[seg_idx]),
            edge_levels=list(edge_levels[seg_idx]),
        )
        if decoded is not None:
            results.append(decoded)

    logging.info(
        f"Decoded {len(results)} barcodes from {len(segments)} edge segments "
        f"on ephys line {barcode_bnc_line} (column: {timestamp_column})"
    )
    return results


def align_session_to_ephys(
    session_dir: str | Path,
    ephys_events: pd.DataFrame,
    barcode_bnc_line: int,
    timestamp_column: str = "timestamps",
    barcode_config: Optional[BarcodeConfig] = None,
) -> tuple[pd.DataFrame, dict]:
    """Align MSW session trials to the ephys clock using TTL barcode events.

    Loads the session df, decodes barcodes from ephys events, matches them by
    barcode_value, fits a linear clock model (ephys = slope * bpod + intercept),
    and adds aligned timestamp columns to the trial df.

    Args:
        session_dir:      Path to the MSW session directory.
        ephys_events:     Events df from open-ephys-python-tools.
        barcode_bnc_line: Digital line number for the barcode channel.
        timestamp_column: Timestamp column to use from ephys_events.
                          Use "corrected_timestamps" if global processor alignment
                          was run (recommended for behaviour alignment).
        barcode_config:   Must match the config used during acquisition.

    Returns:
        df:               Trial df with added columns:
                            trial_start_ephys     - ephys time for every trial start
                            barcode_ephys_time    - matched ephys time per barcode trial
                            alignment_slope
                            alignment_intercept
                            n_barcodes_matched
        result:           Dict with alignment diagnostics:
                            slope, intercept, n_matched,
                            bpod_anchors, ephys_anchors,
                            residuals_ms, bpod_to_ephys (callable)
    """
    session_dir = Path(session_dir)
    if barcode_config is None:
        barcode_config = BarcodeConfig.default()

    # --- Load MSW session ---
    session_data = read_session_data(session_dir)
    df = session_data.get("df")
    if df is None:
        raise ValueError(f"Could not load trial df from {session_dir}")

    # --- Extract barcode info from MSW df ---
    # After read_trial_df, "barcode_value" is a column from the expanded info dict.
    # "barcode_start" is a column from the expanded States timestamps dict.
    if "barcode_value" not in df.columns:
        raise ValueError(
            "No 'barcode_value' column in session df. "
            "Was this session recorded with barcode integration?"
        )

    has_barcode = df["barcode_value"].notna()
    barcode_rows = df[has_barcode]

    if barcode_rows.empty:
        raise ValueError("No barcode trials found in session df.")

    if BARCODE_FIRST_STATE_NAME not in df.columns:
        raise ValueError(
            f"State column '{BARCODE_FIRST_STATE_NAME}' not found in df. "
            f"Check that inject_barcode_states() used first_state_name='{BARCODE_FIRST_STATE_NAME}'."
        )

    def _extract_state_start(cell) -> float:
        """Get start time from a Bpod state timestamp cell [[t_start, t_end]]."""
        try:
            t = cell[0][0]
            return float(t) if not np.isnan(t) else np.nan
        except (TypeError, IndexError, ValueError):
            return np.nan

    # State timestamps in pybpod are trial-relative (reset to ~0 each trial).
    # Add the session-absolute trial start to get session-absolute barcode times.
    bpod_barcode_times = (
        barcode_rows[BARCODE_FIRST_STATE_NAME].apply(_extract_state_start)
        + barcode_rows["Trial start timestamp"]
    )
    msw_barcode_values = barcode_rows["barcode_value"].astype(int)

    # --- Decode barcodes from ephys ---
    ephys_barcodes = decode_ephys_barcodes(
        ephys_events=ephys_events,
        barcode_bnc_line=barcode_bnc_line,
        timestamp_column=timestamp_column,
        barcode_config=barcode_config,
    )

    if not ephys_barcodes:
        raise ValueError("No barcodes decoded from ephys events.")

    ephys_lookup: dict[int, float] = {int(bv): et for et, bv in ephys_barcodes}

    # --- Match barcodes by value ---
    bpod_anchors = []
    ephys_anchors = []
    matched_indices = []

    for idx, (bpod_t, bv) in zip(barcode_rows.index, zip(bpod_barcode_times, msw_barcode_values)):
        if np.isnan(bpod_t):
            logging.debug(f"  Skipping barcode at index {idx}: NaN bpod time")
            continue
        bv_int = int(bv)
        if bv_int in ephys_lookup:
            bpod_anchors.append(bpod_t)
            ephys_anchors.append(ephys_lookup[bv_int])
            matched_indices.append(idx)
        else:
            logging.debug(f"  Barcode value {bv_int} not found in ephys decode.")

    n_matched = len(bpod_anchors)
    n_msw = len(barcode_rows)
    n_ephys = len(ephys_barcodes)
    logging.info(f"Matched {n_matched}/{n_msw} MSW barcodes to {n_ephys} ephys barcodes.")

    if n_matched < 2:
        raise ValueError(
            f"Need at least 2 matched barcodes for alignment, got {n_matched}. "
            f"MSW had {n_msw} barcodes, ephys decoded {n_ephys}."
        )

    # --- Linear fit: ephys_time = slope * bpod_time + intercept ---
    bpod_arr = np.array(bpod_anchors, dtype=float)
    ephys_arr = np.array(ephys_anchors, dtype=float)
    valid = np.isfinite(bpod_arr) & np.isfinite(ephys_arr)
    logging.info(
        f"Anchor pairs: bpod={bpod_arr.tolist()} ephys={ephys_arr.tolist()} "
        f"finite={valid.sum()}/{len(valid)}"
    )
    if valid.sum() < 2:
        raise ValueError(
            f"Not enough finite anchor pairs for linear fit: "
            f"{valid.sum()} valid of {len(valid)} matched. "
            f"bpod={bpod_arr.tolist()} ephys={ephys_arr.tolist()}"
        )
    slope, intercept = np.polyfit(bpod_arr[valid], ephys_arr[valid], deg=1)

    def bpod_to_ephys(bpod_t):
        return slope * bpod_t + intercept

    residuals_ms = [
        (ephys_t - bpod_to_ephys(bpod_t)) * 1000
        for bpod_t, ephys_t in zip(bpod_anchors, ephys_anchors)
    ]
    logging.info(
        f"Alignment: slope={slope:.8f}, intercept={intercept:.4f}s | "
        f"residuals max={max(abs(r) for r in residuals_ms):.2f}ms "
        f"mean={np.mean(np.abs(residuals_ms)):.2f}ms"
    )

    # --- Add aligned columns to df ---
    df["trial_start_ephys"] = df["Trial start timestamp"].apply(bpod_to_ephys)

    df["barcode_ephys_time"] = np.nan
    for idx, ephys_t in zip(matched_indices, ephys_anchors):
        df.at[idx, "barcode_ephys_time"] = ephys_t

    df["alignment_slope"] = slope
    df["alignment_intercept"] = intercept
    df["n_barcodes_matched"] = n_matched

    result = {
        "slope": slope,
        "intercept": intercept,
        "n_matched": n_matched,
        "n_msw_barcodes": n_msw,
        "n_ephys_barcodes": n_ephys,
        "bpod_anchors": bpod_anchors,
        "ephys_anchors": ephys_anchors,
        "residuals_ms": residuals_ms,
        "bpod_to_ephys": bpod_to_ephys,
        "timestamp_column_used": timestamp_column,
    }

    return df, result


def decode_rpi_ttl_in(
    ttl_in_npz: str | Path,
    barcode_config: Optional[BarcodeConfig] = None,
) -> list[tuple[float, int]]:
    """Decode barcodes from an rpi_camera_ensemble ttl_in.npz file.

    The rpi receiver stores (unix_timestamp, level) for every edge on the TTL-in
    pin. Edge timestamps are wall-clock Unix time (time.time() in the pigpio
    callback), not an ephys clock, so they can be compared directly to
    barcode_wall_time saved in the MSW trial df.

    Args:
        ttl_in_npz:     Path to the .ttl_in.npz file written by the rpi agent.
        barcode_config: Must match the config used during acquisition.

    Returns:
        List of (unix_time, barcode_value) tuples, one per decoded barcode.
        unix_time is the wall-clock time of the first edge of that barcode.
    """
    if barcode_config is None:
        barcode_config = BarcodeConfig.default()

    data = np.load(ttl_in_npz, allow_pickle=True)
    edge_times = data["timestamp"].astype(float)
    edge_levels = data["data"].astype(bool)

    if len(edge_times) == 0:
        logging.warning(f"ttl_in file is empty: {ttl_in_npz}")
        return []

    barcoder = BarcodeTTL(barcode_config)

    gap_indices = np.where(np.diff(edge_times) > _INTER_BARCODE_GAP_S)[0] + 1
    segments = np.split(np.arange(len(edge_times)), gap_indices)

    results = []
    for seg_idx in segments:
        if len(seg_idx) < 6:
            continue
        decoded = barcoder.decode_edges(
            edge_timestamps=list(edge_times[seg_idx]),
            edge_levels=list(edge_levels[seg_idx]),
        )
        if decoded is not None:
            results.append(decoded)

    logging.info(
        f"rpi ttl_in: {len(results)} decoded from {len(segments)} segments "
        f"({len(edge_times)} total edges)"
    )
    return results


def verify_rpi_barcode_decoding(
    session_dir: str | Path,
    ttl_in_npz: str | Path,
    barcode_config: Optional[BarcodeConfig] = None,
) -> dict:
    """Check that rpi-recorded TTL edges are decodable and match the MSW session.

    Compares decoded barcodes from the rpi ttl_in.npz against barcode_value
    entries in the MSW trial df. Reports decode rate, match rate, and timing
    error between rpi unix timestamps and barcode_wall_time saved per trial.

    This is the primary post-session check for _test_barcode_iti_with_video.

    Args:
        session_dir:    MSW session directory.
        ttl_in_npz:     Path to the rpi agent's ttl_in.npz.
        barcode_config: Must match acquisition config.

    Returns:
        Dict with verification summary:
            n_msw_barcodes, n_rpi_decoded, n_matched,
            decode_rate, match_rate,
            wall_time_errors_ms  (rpi unix time vs barcode_wall_time per match),
            wall_time_error_max_ms, wall_time_error_mean_ms,
            unmatched_msw_values, unmatched_rpi_values
    """
    if barcode_config is None:
        barcode_config = BarcodeConfig.default()

    session_data = read_session_data(Path(session_dir))
    df = session_data.get("df")
    if df is None:
        raise ValueError(f"Could not load trial df from {session_dir}")

    if "barcode_value" not in df.columns:
        raise ValueError("No barcode_value column — was this a barcode test session?")

    barcode_rows = df[df["barcode_value"].notna()].copy()
    msw_values = barcode_rows["barcode_value"].astype(int).tolist()
    msw_wall_times = barcode_rows["barcode_wall_time"].tolist()

    rpi_decoded = decode_rpi_ttl_in(ttl_in_npz, barcode_config)
    rpi_lookup: dict[int, float] = {int(bv): t for t, bv in rpi_decoded}

    wall_time_errors_ms = []
    matched_values = []
    for bv, wt in zip(msw_values, msw_wall_times):
        if bv in rpi_lookup:
            error_ms = (rpi_lookup[bv] - wt) * 1000
            wall_time_errors_ms.append(error_ms)
            matched_values.append(bv)

    n_msw = len(msw_values)
    n_rpi = len(rpi_decoded)
    n_matched = len(matched_values)

    unmatched_msw = [v for v in msw_values if v not in rpi_lookup]
    unmatched_rpi = [int(bv) for _, bv in rpi_decoded if int(bv) not in set(msw_values)]

    result = {
        "n_msw_barcodes": n_msw,
        "n_rpi_decoded": n_rpi,
        "n_matched": n_matched,
        "decode_rate": n_rpi / n_msw if n_msw else 0.0,
        "match_rate": n_matched / n_msw if n_msw else 0.0,
        "wall_time_errors_ms": wall_time_errors_ms,
        "wall_time_error_max_ms": max(abs(e) for e in wall_time_errors_ms) if wall_time_errors_ms else None,
        "wall_time_error_mean_ms": float(np.mean(np.abs(wall_time_errors_ms))) if wall_time_errors_ms else None,
        "unmatched_msw_values": unmatched_msw,
        "unmatched_rpi_values": unmatched_rpi,
    }

    logging.info(
        f"rpi barcode verification: {n_matched}/{n_msw} matched "
        f"(decode rate {result['decode_rate']:.1%}, match rate {result['match_rate']:.1%}) | "
        f"wall time error: mean {result['wall_time_error_mean_ms']:.1f}ms "
        f"max {result['wall_time_error_max_ms']:.1f}ms"
        if wall_time_errors_ms else
        f"rpi barcode verification: 0/{n_msw} matched — no barcodes decoded from rpi."
    )

    return result
