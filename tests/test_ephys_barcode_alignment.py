"""
Test: Open Ephys barcode decoding + alignment to MSW session.

Loads an Open Ephys record node directory, finds digital events on a
specified line, decodes barcodes, and aligns to the MSW session df.

Usage
-----
python test_ephys_barcode_alignment.py \
    --session  /data/subject/session_dir \
    --oe_dir   /data/subject/ephys_dir/Record\ Node\ 101 \
    --line     8 \
    --ts_col   corrected_timestamps

# Use raw timestamps (no processor alignment):
python test_ephys_barcode_alignment.py \
    --session /data/subject/session_dir \
    --oe_dir  /path/to/Record\ Node\ 101 \
    --line    8 \
    --ts_col  timestamps

# Different barcode config:
    --bits 37 --bit_duration_ms 35.0 --init_duration_ms 10.0

Notes on OE events df
---------------------
Loaded via open-ephys-python-tools:
    session.recordnodes[0].recordings[0].events
Columns:
    line             : digital channel number (1-indexed, matches Bpod BNC number directly)
    state            : 1 = rising (HIGH), 0 = falling (LOW)
    timestamps       : raw ephys clock (seconds)
    corrected_timestamps : global-aligned clock, present if Timestamps Synchronizer
                           processor was upstream of the Record Node (recommended)

Default --line 8 corresponds to the rig-specific mapping of Bpod BNC2 → ephys
digital input. Change --line to match your rig's wiring.

Expected output (passing):
    n_matched / n_msw  : equal
    residuals_mean_ms  : <5ms
    residuals_max_ms   : <20ms
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from murineshiftwork.readers.alignment import align_session_to_ephys, decode_ephys_barcodes
from ttl_barcoder.core.config import BarcodeConfig


def load_oe_events(oe_dir: Path, recording_index: int = 0):
    """Load events DataFrame from an Open Ephys record node directory."""
    try:
        from open_ephys.analysis import Session
    except ImportError:
        raise ImportError(
            "open-ephys-python-tools not installed. "
            "pip install open-ephys-python-tools"
        )
    session = Session(str(oe_dir))
    if hasattr(session, "recordnodes"):
        recording = session.recordnodes[0].recordings[recording_index]
    else:
        recording = session.recordings[recording_index]
    events = recording.events
    return events


def inspect_events(events, line: int, ts_col: str):
    """Print summary of events on the barcode line."""
    all_lines = sorted(events["line"].unique())
    print(f"Available lines in OE events: {all_lines}")

    line_df = events[events["line"] == line].sort_values(ts_col)
    print(f"Events on line {line}         : {len(line_df)}")

    if len(line_df) == 0:
        print(f"  WARNING: no events on line {line}. Check wiring and --line argument.")
        return

    duration = line_df[ts_col].iloc[-1] - line_df[ts_col].iloc[0]
    print(f"Time span                   : {duration:.1f}s ({duration/60:.1f}min)")

    inter = np.diff(line_df[ts_col].values)
    print(f"Inter-edge gaps (ms)        : "
          f"min={inter.min()*1000:.1f}  "
          f"median={np.median(inter)*1000:.1f}  "
          f"max={inter.max()*1000:.0f}")

    short = (inter < 0.5).sum()
    long_ = (inter >= 0.5).sum()
    print(f"Gaps <500ms (within barcode): {short}   >=500ms (between barcodes): {long_}")

    rising = (line_df["state"] == 1).sum()
    falling = (line_df["state"] == 0).sum()
    print(f"Rising edges: {rising}   Falling edges: {falling}")


def main():
    parser = argparse.ArgumentParser(description="Align MSW session to ephys via barcode TTL.")
    parser.add_argument("--session", required=True, help="MSW session directory")
    parser.add_argument("--oe_dir", required=True, help="Open Ephys Record Node directory")
    parser.add_argument("--line", type=int, default=8,
                        help="Digital line number for barcode channel (default: 8)")
    parser.add_argument("--ts_col", default="corrected_timestamps",
                        help="Timestamp column to use: 'timestamps' or 'corrected_timestamps' (default)")
    parser.add_argument("--recording", type=int, default=0,
                        help="Recording index within the record node (default: 0)")
    parser.add_argument("--bits", type=int, default=37)
    parser.add_argument("--bit_duration_ms", type=float, default=35.0)
    parser.add_argument("--init_duration_ms", type=float, default=10.0)
    args = parser.parse_args()

    session_dir = Path(args.session)
    oe_dir = Path(args.oe_dir)
    assert session_dir.exists(), f"Session dir not found: {session_dir}"
    assert oe_dir.exists(), f"OE dir not found: {oe_dir}"

    barcode_config = BarcodeConfig(
        barcode_bits=args.bits,
        bit_duration_ms=args.bit_duration_ms,
        init_duration_ms=args.init_duration_ms,
    )

    print(f"\nSession   : {session_dir}")
    print(f"OE dir    : {oe_dir}")
    print(f"Line      : {args.line}")
    print(f"TS column : {args.ts_col}")
    print(f"Config    : {barcode_config}\n")

    # --- Load OE events ---
    print("Loading OE events...")
    events = load_oe_events(oe_dir, recording_index=args.recording)
    print(f"Total OE events: {len(events)}")

    if args.ts_col not in events.columns:
        available = list(events.columns)
        print(f"WARNING: '{args.ts_col}' not in events columns: {available}")
        fallback = "timestamps"
        print(f"Falling back to '{fallback}'")
        args.ts_col = fallback

    print()
    inspect_events(events, line=args.line, ts_col=args.ts_col)
    print()

    # --- Decode barcodes from ephys only (no MSW session needed for this step) ---
    print("Decoding barcodes from ephys edges...")
    ephys_barcodes = decode_ephys_barcodes(
        ephys_events=events,
        barcode_bnc_line=args.line,
        timestamp_column=args.ts_col,
        barcode_config=barcode_config,
    )
    print(f"Decoded {len(ephys_barcodes)} barcodes from OE events\n")

    if not ephys_barcodes:
        print("FAIL — no barcodes decoded. Check line number and wiring.")
        return 1

    # Show a few decoded values and their recovered timestamps
    print("Sample decoded barcodes (ephys_time, barcode_value, recovered_unix_time):")
    from ttl_barcoder.core.barcode_ttl import BarcodeTTL
    barcoder = BarcodeTTL(barcode_config)
    import time as _time
    for et, bv in ephys_barcodes[:5]:
        try:
            # Use current wall time as reference (bv encodes Unix ms mod 2^37)
            recovered_unix = barcoder.recover_timestamp(bv, reference_time=_time.time())
            print(f"  ephys={et:.4f}s  value={bv}  recovered_unix={recovered_unix:.3f}")
        except Exception:
            print(f"  ephys={et:.4f}s  value={bv}")
    if len(ephys_barcodes) > 5:
        print(f"  ... ({len(ephys_barcodes) - 5} more)")
    print()

    # --- Full alignment to MSW session ---
    print("Aligning MSW session to ephys clock...")
    try:
        df, result = align_session_to_ephys(
            session_dir=session_dir,
            ephys_events=events,
            barcode_bnc_line=args.line,
            timestamp_column=args.ts_col,
            barcode_config=barcode_config,
        )
    except ValueError as e:
        print(f"FAIL — alignment error: {e}")
        return 1

    print("\n=== Alignment result ===")
    print(f"MSW barcodes        : {result['n_msw_barcodes']}")
    print(f"Ephys decoded       : {result['n_ephys_barcodes']}")
    print(f"Matched             : {result['n_matched']}")
    print(f"Slope               : {result['slope']:.8f}  (1.0 = no drift)")
    print(f"Intercept           : {result['intercept']:.4f}s")

    if result["residuals_ms"]:
        res = result["residuals_ms"]
        print(f"Residuals (ms)      : mean={float(np.mean(np.abs(res))):.2f}  "
              f"max={float(max(abs(r) for r in res)):.2f}  "
              f"std={float(np.std(res)):.2f}")

    print(f"\nAdded columns to df : trial_start_ephys, barcode_ephys_time, "
          f"alignment_slope, alignment_intercept, n_barcodes_matched")
    print(f"df shape            : {df.shape}")

    # Show first few trial_start_ephys values
    if "trial_start_ephys" in df.columns:
        task_rows = df[df.get("trial_type", df.index) == "task"] if "trial_type" in df.columns else df
        print(f"\nSample trial_start_ephys (first 5 task trials):")
        sample = task_rows["trial_start_ephys"].dropna().head(5)
        for i, t in sample.items():
            print(f"  trial {i}: {t:.4f}s ephys")

    print()
    passed = (
        result["n_matched"] == result["n_msw_barcodes"]
        and float(np.mean(np.abs(result["residuals_ms"]))) < 5.0
    )
    print("PASS" if passed else
          f"WARN — check residuals or unmatched barcodes "
          f"(matched {result['n_matched']}/{result['n_msw_barcodes']})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
