"""
Plot inter-pulse interval distributions for ephys digital lines.

Useful for visualising camera TTL jitter as recorded by Open Ephys.
Lines 3-6 receive RPI camera encoder frame pulses by default.

Usage
-----
python plot_ephys_line_jitter.py --oe_dir /path/to/Record\ Node\ 101
python plot_ephys_line_jitter.py --oe_dir /path/to/Record\ Node\ 101 --lines 3 4 5 6 --ts_col corrected_timestamps --edge rising
python plot_ephys_line_jitter.py --oe_dir ... --out jitter.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def load_oe_events(oe_dir: Path, recording_index: int = 0):
    try:
        from open_ephys.analysis import Session
    except ImportError:
        raise ImportError("pip install open-ephys-python-tools")
    session = Session(str(oe_dir))
    if hasattr(session, "recordnodes"):
        rec = session.recordnodes[0].recordings[recording_index]
    else:
        rec = session.recordings[recording_index]
    return rec.events


def get_ipi_ms(events, line: int, ts_col: str, edge: str) -> np.ndarray:
    """Inter-pulse intervals in ms for one line, filtered by edge direction."""
    df = events[events["line"] == line].sort_values(ts_col)
    if edge == "rising":
        df = df[df["state"] == 1]
    elif edge == "falling":
        df = df[df["state"] == 0]
    if len(df) < 2:
        return np.array([])
    return np.diff(df[ts_col].values) * 1000.0


def main():
    parser = argparse.ArgumentParser(description="Plot ephys digital line IPI distributions.")
    parser.add_argument("--oe_dir", required=True, help="Open Ephys Record Node directory")
    parser.add_argument("--lines", type=int, nargs="+", default=[3, 4, 5, 6],
                        help="Digital line numbers to plot (default: 3 4 5 6)")
    parser.add_argument("--ts_col", default="timestamps",
                        help="Timestamp column: timestamps or corrected_timestamps (default: timestamps)")
    parser.add_argument("--edge", default="rising", choices=["rising", "falling", "both"],
                        help="Which edges to use for IPI computation (default: rising)")
    parser.add_argument("--clip_ms", type=float, default=None,
                        help="Clip IPIs above this value before plotting (e.g. 100 to ignore dropped frames)")
    parser.add_argument("--out", default=None, help="Save figure to this path instead of showing")
    args = parser.parse_args()

    oe_dir = Path(args.oe_dir)
    print(f"Loading OE events from: {oe_dir}")
    events = load_oe_events(oe_dir)

    available = sorted(events["line"].unique())
    print(f"Available lines: {available}")

    palette = sns.color_palette("tab10", n_colors=len(args.lines))

    sns.set_theme(style="ticks", font_scale=1.6)
    fig, ax = plt.subplots(figsize=(11, 6))

    any_data = False
    for color, line in zip(palette, args.lines):
        ipi = get_ipi_ms(events, line, args.ts_col, args.edge)
        if len(ipi) == 0:
            print(f"  Line {line}: no events, skipping")
            continue

        if args.clip_ms is not None:
            n_before = len(ipi)
            ipi = ipi[ipi <= args.clip_ms]
            n_clipped = n_before - len(ipi)
            if n_clipped:
                print(f"  Line {line}: clipped {n_clipped} IPIs > {args.clip_ms}ms")

        mean_ms = ipi.mean()
        median_ms = np.median(ipi)
        std_ms = ipi.std()
        freq_hz = 1000.0 / mean_ms
        n = len(ipi)

        label = (
            f"Line {line}  "
            f"n={n}  "
            f"{freq_hz:.2f}Hz  "
            f"mean={mean_ms:.2f}ms  "
            f"med={median_ms:.2f}ms  "
            f"std={std_ms:.3f}ms"
        )
        print(f"  line {line}: {freq_hz:.2f}Hz  mean={mean_ms:.2f}ms  med={median_ms:.2f}ms  std={std_ms:.3f}ms  n={n}")

        # Compute KDE manually so we can normalize peak to 1.0.
        # This makes shape comparison across lines independent of n and spread.
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(ipi)
        x_grid = np.linspace(ipi.min(), ipi.max(), 1000)
        y_kde = kde(x_grid)
        y_norm = y_kde / y_kde.max()
        ax.plot(x_grid, y_norm, color=color, linewidth=2, label=label)
        ax.fill_between(x_grid, y_norm, alpha=0.25, color=color)
        ax.axvline(mean_ms,   color=color, linestyle="--", linewidth=1.8, alpha=0.9)
        ax.axvline(median_ms, color=color, linestyle=":",  linewidth=1.8, alpha=0.9)
        any_data = True

    if not any_data:
        print("No data found on any requested line. Check --lines and --oe_dir.")
        sys.exit(1)

    # Reference lines for common acquisition frequencies
    for target_hz, label_hz in [(100, "100 Hz"), (60, "60 Hz"), (30, "30 Hz")]:
        x_ms = 1000.0 / target_hz
        ax.axvline(x_ms, color="grey", linewidth=1.4, alpha=0.8, zorder=0)
        ax.text(
            x_ms, 0, f" {label_hz}",
            color="grey", fontsize=13, alpha=0.9,
            va="bottom", ha="left", rotation=90,
            transform=ax.get_xaxis_transform(),
        )

    ax.set_xlabel("Inter-pulse interval (ms)", fontsize=18)
    ax.set_ylabel("Normalized density (peak = 1)", fontsize=18)
    ax.set_ylim(0, 1.05)
    edge_label = args.edge if args.edge != "both" else "all"
    ax.set_title(
        f"Ephys digital line IPI — {oe_dir.name}\n"
        f"edges: {edge_label}   ts: {args.ts_col}   (-- mean  ··· median)",
        fontsize=16,
    )
    ax.legend(fontsize=13, frameon=False, loc="upper right")
    sns.despine(ax=ax)
    fig.tight_layout()

    if args.out:
        fig.savefig(args.out, dpi=150)
        print(f"Saved: {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
