#!/usr/bin/env python3
"""Probe all setups: connect to each Bpod in sequence and print hardware info.

Replicates the _test_bpod_connect task output without creating session files.
Logs connection attempts (retries, timing) and prints a summary table.

Usage:
    python3 scripts/probe_bpods.py
    python3 scripts/probe_bpods.py --config-dir /mnt/maindata/msw_configs
    python3 scripts/probe_bpods.py --setups setup-1 setup-npxb   # subset
    python3 scripts/probe_bpods.py --retries 5 --retry-delay 3.0
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Result


@dataclass
class ProbeResult:
    setup: str
    port_by_path: str = ""
    port_resolved: str = ""
    status: str = "unknown"   # ok | fail | no_port | no_bpod | skip
    reason: str = ""
    hw_info: str = ""         # formatted hardware description
    log_capture: str = ""     # WARNING+ log records captured during probe
    elapsed_s: float = 0.0


# ---------------------------------------------------------------------------
# Hardware info box (mirrors _test_bpod_connect.Task.run)

_MACHINE_NAMES = {1: "r0.5", 2: "r0.7", 3: "r2.0", 4: "r2+"}


def _info_box(pairs: list[tuple[str, str]]) -> str:
    key_w = max(len(k) for k, _ in pairs)
    lines = [f"{k:<{key_w}} : {v}" for k, v in pairs]
    width = max(len(line) for line in lines)
    bar = "+" + "-" * (width + 4) + "+"
    rows = [bar]
    for line in lines:
        rows.append(f"|  {line:<{width}}  |")
    rows.append(bar)
    return "\n".join(rows)


def _build_hw_info(bpod) -> str:
    hw = bpod._bpod._hardware
    mt = getattr(hw, "machine_type", None)
    fw = getattr(hw, "firmware_version", "?")
    pairs = [
        ("serial port",       str(bpod.serial_port)),
        ("port config",       str(getattr(bpod, "_port_config", "?"))),
        ("firmware version",  str(fw)),
        ("machine type",      _MACHINE_NAMES.get(mt, f"unknown ({mt})") if isinstance(mt, int) else f"unknown ({mt})"),
        ("n global timers",   str(getattr(hw, "n_global_timers", "?"))),
        ("n global counters", str(getattr(hw, "n_global_counters", "?"))),
        ("n conditions",      str(getattr(hw, "n_conditions", "?"))),
        ("max serial events", str(getattr(hw, "max_serial_events", "?"))),
        ("max states",        str(getattr(hw, "max_states", "?"))),
        ("cycle frequency",   str(getattr(hw, "cycle_frequency", "?"))),
    ]
    return _info_box(pairs)


# ---------------------------------------------------------------------------
# Config helpers


def _read_config_dir() -> Path:
    try:
        from murineshiftwork.logic.machine_config import read_machine_config
        mc = read_machine_config()
        if mc.get("config_dir"):
            return Path(mc["config_dir"])
    except Exception:
        pass
    return Path("/mnt/maindata/msw_configs")


def _find_setup_files(config_dir: Path, names: list[str]) -> list[Path]:
    if names:
        files = []
        for n in names:
            stem = n if n.startswith("setup-") else f"setup-{n}"
            p = config_dir / "setups" / f"{stem}.yaml"
            if not p.exists():
                print(f"  WARN: {p} not found — skipping", file=sys.stderr)
            else:
                files.append(p)
        return sorted(files)
    return sorted(config_dir.glob("setups/setup-*.yaml"))


# ---------------------------------------------------------------------------
# Per-setup probe


def probe_setup(
    setup_file: Path,
    connect_retries: int,
    retry_delay_s: float,
) -> ProbeResult:
    from murineshiftwork.logic.config.models import SetupConfig

    result = ProbeResult(setup=setup_file.stem)

    # Load and validate setup config
    try:
        data = yaml.safe_load(setup_file.read_text())
        cfg = SetupConfig.model_validate(data)
    except Exception as exc:
        result.status = "skip"
        result.reason = f"config parse error: {exc}"
        return result

    # Find bpod device
    bpod_device = next((d for d in cfg.devices.values() if d.type == "bpod"), None)
    if bpod_device is None:
        result.status = "no_bpod"
        result.reason = "no bpod device in setup config"
        return result

    result.port_by_path = bpod_device.port_by_path

    # Resolve /dev/tty path
    try:
        result.port_resolved = bpod_device.resolve_port()
    except ValueError as exc:
        result.status = "no_port"
        result.reason = str(exc)
        return result

    # Capture WARNING+ log from the connection attempt
    log_buf = io.StringIO()
    log_handler = logging.StreamHandler(log_buf)
    log_handler.setLevel(logging.WARNING)
    log_handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
    root = logging.getLogger()
    root.addHandler(log_handler)

    t0 = time.monotonic()
    try:
        from murineshiftwork.hardware.bpod.factory import BpodFactory

        factory = BpodFactory(
            serial_port=result.port_resolved,
            connect_retries=connect_retries,
            retry_delay_s=retry_delay_s,
        )
        factory.open()
        try:
            result.hw_info = _build_hw_info(factory)
            result.status = "ok"
        finally:
            factory.close_safely()

    except Exception as exc:
        result.status = "fail"
        result.reason = str(exc)

    finally:
        result.elapsed_s = time.monotonic() - t0
        log_handler.flush()
        result.log_capture = log_buf.getvalue().strip()
        root.removeHandler(log_handler)

    return result


# ---------------------------------------------------------------------------
# Reporting

_STATUS_LABEL = {
    "ok":      "  OK  ",
    "fail":    " FAIL ",
    "no_port": "NOPORT",
    "no_bpod": "NOBPOD",
    "skip":    " SKIP ",
    "unknown": "  ??  ",
}

_SEP = "=" * 70


def _print_result(r: ProbeResult) -> None:
    label = _STATUS_LABEL.get(r.status, r.status.upper()[:6])
    print(f"\n{_SEP}")
    print(f"[{label}]  {r.setup}  ({r.elapsed_s:.1f} s)")
    if r.port_by_path:
        print(f"  by-path  : {r.port_by_path}")
    if r.port_resolved:
        print(f"  resolved : {r.port_resolved}")
    if r.reason:
        print(f"  reason   : {r.reason}")
    if r.log_capture:
        print("  --- log (WARNING+) ---")
        for line in r.log_capture.splitlines():
            print(f"  {line}")
    if r.hw_info:
        print()
        for line in r.hw_info.splitlines():
            print(f"  {line}")


def _print_summary(results: list[ProbeResult]) -> None:
    print(f"\n{_SEP}")
    print("SUMMARY")
    print(_SEP)
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
        label = _STATUS_LABEL.get(r.status, r.status.upper()[:6])
        port = f"  {r.port_resolved}" if r.port_resolved else ""
        reason = f"  — {r.reason}" if r.reason and r.status != "ok" else ""
        timing = f"  ({r.elapsed_s:.1f} s)" if r.elapsed_s else ""
        print(f"  [{label}]  {r.setup}{port}{timing}{reason}")
    print()
    for status, count in sorted(counts.items()):
        print(f"  {_STATUS_LABEL.get(status, status)}: {count}")
    print()


# ---------------------------------------------------------------------------
# Entry point


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Config directory (default: from machine config or /mnt/maindata/msw_configs)",
    )
    parser.add_argument(
        "--setups",
        nargs="+",
        metavar="NAME",
        default=[],
        help="Probe only these setups (e.g. setup-1 npxb). Default: all setup-*.yaml.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        dest="connect_retries",
        help="Bpod connection retries per setup (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        dest="retry_delay_s",
        help="Seconds to wait between connection retries (default: 2.0)",
    )
    args = parser.parse_args()

    config_dir = args.config_dir or _read_config_dir()
    setup_files = _find_setup_files(config_dir, args.setups)

    if not setup_files:
        print("No setup files found.", file=sys.stderr)
        sys.exit(1)

    # Root logger: DEBUG level so BpodFactory retry warnings are captured
    logging.basicConfig(level=logging.DEBUG, handlers=[])

    print(f"Config dir : {config_dir}")
    print(f"Setups     : {len(setup_files)}")
    print(f"Retries    : {args.connect_retries}  delay: {args.retry_delay_s} s")

    results: list[ProbeResult] = []
    for setup_file in setup_files:
        print(f"\nProbing {setup_file.stem} ...", flush=True)
        r = probe_setup(
            setup_file,
            connect_retries=args.connect_retries,
            retry_delay_s=args.retry_delay_s,
        )
        results.append(r)
        _print_result(r)

    _print_summary(results)
    sys.exit(1 if any(r.status == "fail" for r in results) else 0)


if __name__ == "__main__":
    main()
