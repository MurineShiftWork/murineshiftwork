"""
Test: RCE ttl_in.npz barcode decoding vs MSW session.

Run this after a _test_barcode_iti_with_video session to verify that the
barcode pulses recorded by the rpi TTL-in receiver are correctly decoded
and match the MSW session data.

Usage
-----
# Minimal — auto-discovers ttl_in.npz from session dir:
python test_rce_barcode_alignment.py --session /data/subject/session_dir

# Explicit paths:
python test_rce_barcode_alignment.py \
    --session /data/subject/session_dir \
    --ttl_in /data/subject/session_dir/session.rce.rpi-12.20260502.ttl_in.npz

# Different barcode config (must match what the task used):
python test_rce_barcode_alignment.py \
    --session /data/subject/session_dir \
    --bits 37 --bit_duration_ms 35.0 --init_duration_ms 10.0

Expected output (passing):
    decode_rate  : 1.000  (all MSW barcodes found in rpi edges)
    match_rate   : 1.000
    wall_time_error_mean_ms: <50ms  (NTP sync + pigpio latency)
    wall_time_error_max_ms : <200ms
    unmatched_msw_values   : []
"""
import argparse
import pprint
import sys
from glob import glob
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from murine_shift_work.readers.alignment import verify_rpi_barcode_decoding
from ttl_barcoder.core.config import BarcodeConfig


def find_ttl_in(session_dir: Path) -> Path | None:
    """Auto-discover ttl_in.npz in the session dir."""
    hits = glob(str(session_dir / "*.ttl_in.npz"))
    if len(hits) == 1:
        return Path(hits[0])
    if len(hits) > 1:
        print(f"Multiple ttl_in.npz found — specify with --ttl_in:")
        for h in hits:
            print(f"  {h}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Verify rpi barcode decoding against MSW session.")
    parser.add_argument("--session", required=True, help="MSW session directory")
    parser.add_argument("--ttl_in", default=None, help="Path to ttl_in.npz (auto-discovered if omitted)")
    parser.add_argument("--bits", type=int, default=37)
    parser.add_argument("--bit_duration_ms", type=float, default=35.0)
    parser.add_argument("--init_duration_ms", type=float, default=10.0)
    args = parser.parse_args()

    session_dir = Path(args.session)
    assert session_dir.exists(), f"Session dir not found: {session_dir}"

    ttl_in = Path(args.ttl_in) if args.ttl_in else find_ttl_in(session_dir)
    if ttl_in is None:
        # also try current working directory
        ttl_in_cwd = list(Path(".").glob("*.ttl_in.npz"))
        if len(ttl_in_cwd) == 1:
            ttl_in = ttl_in_cwd[0]
            print(f"Found ttl_in.npz in cwd: {ttl_in}")
    assert ttl_in is not None and ttl_in.exists(), \
        f"ttl_in.npz not found. Use --ttl_in to specify path."

    barcode_config = BarcodeConfig(
        barcode_bits=args.bits,
        bit_duration_ms=args.bit_duration_ms,
        init_duration_ms=args.init_duration_ms,
    )

    print(f"\nSession   : {session_dir}")
    print(f"ttl_in    : {ttl_in}")
    print(f"Config    : {barcode_config}\n")

    # --- Raw edge inspection ---
    data = np.load(ttl_in, allow_pickle=True)
    edge_times = data["timestamp"]
    edge_levels = data["data"]
    print(f"Raw edges in ttl_in.npz : {len(edge_times)}")
    if len(edge_times) > 0:
        session_duration = edge_times[-1] - edge_times[0]
        print(f"Edge time span          : {session_duration:.1f}s ({session_duration/60:.1f}min)")
        inter_edge = np.diff(edge_times)
        print(f"Inter-edge gaps (ms)    : "
              f"min={inter_edge.min()*1000:.1f}  "
              f"median={np.median(inter_edge)*1000:.1f}  "
              f"max={inter_edge.max()*1000:.0f}")
        # Show gap histogram to distinguish within-barcode vs between-barcode gaps
        short = (inter_edge < 0.5).sum()
        long_ = (inter_edge >= 0.5).sum()
        print(f"Gaps <500ms (within barcode): {short}   >=500ms (between barcodes): {long_}")
    print()

    # --- Decode and verify ---
    result = verify_rpi_barcode_decoding(
        session_dir=session_dir,
        ttl_in_npz=ttl_in,
        barcode_config=barcode_config,
    )

    print("=== Verification result ===")
    print(f"MSW barcodes        : {result['n_msw_barcodes']}")
    print(f"RCE decoded         : {result['n_rpi_decoded']}")
    print(f"Matched             : {result['n_matched']}")
    print(f"Decode rate         : {result['decode_rate']:.3f}")
    print(f"Match rate          : {result['match_rate']:.3f}")

    if result["wall_time_errors_ms"]:
        errs = result["wall_time_errors_ms"]
        print(f"Wall time error (ms): mean={result['wall_time_error_mean_ms']:.1f}  "
              f"max={result['wall_time_error_max_ms']:.1f}  "
              f"std={float(np.std(errs)):.1f}")
        # Positive = rpi saw the barcode later than wall_time (expected: small positive, ~10-100ms)
        print(f"  (positive = rpi edge after MSW wall_time, expected from NTP + pigpio latency)")

    if result["unmatched_msw_values"]:
        print(f"\nUnmatched MSW barcodes ({len(result['unmatched_msw_values'])}):")
        print(f"  {result['unmatched_msw_values']}")

    if result["unmatched_rpi_values"]:
        print(f"\nExtra RCE barcodes not in MSW ({len(result['unmatched_rpi_values'])}):")
        print(f"  {result['unmatched_rpi_values'][:10]}{'...' if len(result['unmatched_rpi_values']) > 10 else ''}")

    print()
    passed = result["match_rate"] == 1.0 and result["decode_rate"] == 1.0
    print("PASS" if passed else "FAIL — check unmatched values above")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
