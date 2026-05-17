"""
Batch barcode decode-rate check across all rce.rpi-*.ttl_in.npz files
in yesterday's sessions under a given base path.

Usage
-----
python tests/batch_rce_barcode_decode_rate.py
python tests/batch_rce_barcode_decode_rate.py --base /ceph/sjones/users/lars/data --date 20260505
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from ttl_barcoder.core.config import BarcodeConfig

from murineshiftwork.readers.alignment import verify_rpi_barcode_decoding

# regex to extract rpi-id from filename, e.g. "...rce.rpi-172.20260505154911.ttl_in.npz"
_RPI_RE = re.compile(r"\.rce\.(rpi-[\w]+)\.\d+\.ttl_in\.npz$")


def find_ttl_in_files(base: Path, date_str: str) -> list[Path]:
    # Two fixed-depth globs: direct sessions and child-of-ephys sessions.
    # Much faster than rglob; avoids scanning unrelated subtrees.
    pat_direct = f"t*/t*{date_str}*/*{date_str}*.ttl_in.npz"
    pat_child = f"t*/t*{date_str}*/t*{date_str}*/*{date_str}*.ttl_in.npz"
    return sorted(set(base.glob(pat_direct)) | set(base.glob(pat_child)))


def rpi_id(path: Path) -> str:
    m = _RPI_RE.search(path.name)
    return m.group(1) if m else "rpi-?"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        default="/ceph/sjones/users/lars/data",
        help="Root data directory",
    )
    parser.add_argument(
        "--date", default="20260505", help="Date string to match (YYYYMMDD)"
    )
    parser.add_argument("--bits", type=int, default=37)
    parser.add_argument("--bit_duration_ms", type=float, default=35.0)
    parser.add_argument("--init_duration_ms", type=float, default=10.0)
    parser.add_argument(
        "--min_barcodes",
        type=int,
        default=10,
        help="Skip sessions with fewer MSW barcodes than this (default: 10)",
    )
    args = parser.parse_args()

    base = Path(args.base)
    barcode_cfg = BarcodeConfig(
        barcode_bits=args.bits,
        bit_duration_ms=args.bit_duration_ms,
        init_duration_ms=args.init_duration_ms,
    )

    ttl_files = find_ttl_in_files(base, args.date)
    if not ttl_files:
        print(f"No ttl_in.npz files found for date {args.date} under {base}")
        sys.exit(1)

    print(f"Found {len(ttl_files)} ttl_in.npz files for {args.date}\n")

    # per-rpi aggregation: list of decode_rates
    rpi_decode_rates: dict[str, list[float]] = defaultdict(list)
    rpi_match_rates: dict[str, list[float]] = defaultdict(list)

    col_w = 55  # width for the session column
    header = f"{'session':<{col_w}}  {'rpi':<10}  {'msw':>5}  {'decoded':>7}  {'matched':>7}  {'dec_rate':>8}  {'match_rate':>10}  status"
    print(header)
    print("-" * len(header))

    for ttl_path in ttl_files:
        session_dir = ttl_path.parent
        rpi = rpi_id(ttl_path)
        session_label = session_dir.name[:col_w]

        try:
            result = verify_rpi_barcode_decoding(
                session_dir=session_dir,
                ttl_in_npz=ttl_path,
                barcode_config=barcode_cfg,
            )
        except Exception as exc:
            print(
                f"{session_label:<{col_w}}  {rpi:<10}  {'':>5}  {'':>7}  {'':>7}  {'':>8}  {'':>10}  ERROR: {exc}"
            )
            rpi_decode_rates[rpi].append(0.0)
            rpi_match_rates[rpi].append(0.0)
            continue

        n_msw = result["n_msw_barcodes"]
        if n_msw < args.min_barcodes:
            print(
                f"{session_label:<{col_w}}  {rpi:<10}  {n_msw:>5}  {'':>7}  {'':>7}  {'':>8}  {'':>10}  SKIP (<{args.min_barcodes} barcodes)"
            )
            continue

        dr = result["decode_rate"]
        mr = result["match_rate"]
        n_dec = result["n_rpi_decoded"]
        n_mat = result["n_matched"]
        status = (
            "OK"
            if dr == 1.0 and mr == 1.0
            else "WARN"
            if dr >= 0.8
            else "FAIL"
        )

        print(
            f"{session_label:<{col_w}}  {rpi:<10}  {n_msw:>5}  {n_dec:>7}  {n_mat:>7}  {dr:>8.3f}  {mr:>10.3f}  {status}"
        )
        rpi_decode_rates[rpi].append(dr)
        rpi_match_rates[rpi].append(mr)

    # Summary by rpi
    print()
    print(
        "=== Summary by rpi (mean decode_rate / match_rate across sessions) ==="
    )
    summary_header = f"{'rpi':<12}  {'sessions':>8}  {'mean_dec_rate':>13}  {'mean_match_rate':>15}  {'min_dec_rate':>12}"
    print(summary_header)
    print("-" * len(summary_header))
    for rpi in sorted(rpi_decode_rates):
        drs = rpi_decode_rates[rpi]
        mrs = rpi_match_rates[rpi]
        mean_dr = float(np.mean(drs))
        mean_mr = float(np.mean(mrs))
        min_dr = float(np.min(drs))
        flag = "  <-- CHECK" if mean_dr < 0.95 else ""
        print(
            f"{rpi:<12}  {len(drs):>8}  {mean_dr:>13.3f}  {mean_mr:>15.3f}  {min_dr:>12.3f}{flag}"
        )


if __name__ == "__main__":
    main()
