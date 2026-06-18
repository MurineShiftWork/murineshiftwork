"""Migrate water calibration CSVs, stage calibration YAMLs, and camera config paths
into /mnt/maindata/msw_configs/setups/*.yaml.

Run once from the repo root:
    python tools/migrate_calibrations_to_setup_yaml.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from murineshiftwork.logic.config_models import ValveCalibration

HOME_MSW = Path.home() / ".murineshiftwork"
CONFIGS_DIR = Path("/mnt/maindata/msw_configs/setups")

# ---------------------------------------------------------------------------
# Per-setup sources

WATER_CSV = {
    "setup-1": HOME_MSW / "calibration.water.setup1.csv",
    "setup-2": HOME_MSW / "calibration.water.setup2.csv",
    "setup-3": HOME_MSW / "calibration.water.setup3.csv",
    "setup-4": HOME_MSW / "calibration.water.setup4.csv",
    "setup_5": HOME_MSW / "calibration.water.setup5.csv",
    "setup_6": HOME_MSW / "calibration.water.setup6.csv",
}

STAGE_YAML = {
    "setup-1": HOME_MSW / "calibration.stage.setup1.yaml",
    "setup-2": HOME_MSW / "calibration.stage.setup2.yaml",
    "setup-3": HOME_MSW / "calibration.stage.setup3.yaml",
    "setup-4": HOME_MSW / "calibration.stage.setup4.yaml",
    "setup_5": HOME_MSW / "calibration.stage.setup5.yaml",
    "setup_6": HOME_MSW / "calibration.stage.setup6.yaml",
}

CAMERA_RCE = {
    "setup-1": HOME_MSW / "setup1-rce.yaml",
    "setup-2": HOME_MSW / "setup2-rce.yaml",
    "setup-3": HOME_MSW / "setup3-rce.yaml",
    "setup-4": HOME_MSW / "setup4-rce.yaml",
    "setup-npxb": HOME_MSW / "setup-npxb-rce.yaml",
}


# ---------------------------------------------------------------------------


def _water_cal_for_setup(csv_path: Path) -> dict[str, dict]:
    """Return {valve_id_str: {updated, points}} for the most-recent session in the CSV."""
    df = pd.read_csv(csv_path)

    # Coerce measurement_time to datetime for recency filtering
    df["measurement_time"] = pd.to_datetime(df["measurement_time"])

    # Use only the most recent calibration session per valve
    # (a "session" = unique date, identified by date part of measurement_time)
    df["_date"] = df["measurement_time"].dt.date
    latest_date = df["_date"].max()
    df = df[df["_date"] == latest_date].copy()

    session_ts = df["measurement_time"].max().isoformat(timespec="seconds")

    df["volume_ul"] = np.round((df["water_weight_g"] / df["n_drops"]) * 1000, 3)
    # CSV stores valve_opening_time in seconds; ValveCalibration expects ms
    df["open_ms"] = df["valve_opening_time"] * 1000

    result = {}
    for valve_id, group in df.groupby("valve_id"):
        group = group.sort_values("open_ms")
        points = [
            [round(float(r["open_ms"]), 3), float(r["volume_ul"])]
            for _, r in group.iterrows()
        ]
        vc = ValveCalibration(updated=session_ts, points=points)
        is_valid, reason = vc.validate()
        status = "PASS" if is_valid else "FAIL"
        print(f"  valve {valve_id}: {status} — {reason}")
        result[str(valve_id)] = {"updated": session_ts, "points": points}
    return result


def _stage_axes_and_positions(stage_path: Path) -> tuple[dict, dict]:
    """Return (axes_dict, known_positions_dict) in SetupConfig format."""
    with stage_path.open() as f:
        s = yaml.safe_load(f)

    axes = {}
    for axis_name, ax in s.get("axes", {}).items():
        # Legacy field: 'id', new field: 'motor_id'
        motor_id = ax.get("motor_id") or ax.get("id")
        axes[axis_name] = {
            "motor_id": motor_id,
            "position_min": ax.get("position_min", 1),
            "position_max": ax.get("position_max", 999),
            "velocity_max": ax.get("velocity_max", 200),
            "operating_mode": ax.get("operating_mode", "OP_POSITION"),
        }

    # Legacy format: known_positions.back.y.position_raw → flatten to .back.y = int
    known_positions: dict = {}
    for pos_name, pos_axes in s.get("known_positions", {}).items():
        known_positions[pos_name] = {}
        for ax_name, ax_val in pos_axes.items():
            if isinstance(ax_val, dict):
                known_positions[pos_name][ax_name] = ax_val.get("position_raw", ax_val)
            else:
                known_positions[pos_name][ax_name] = int(ax_val)
    return axes, known_positions


# ---------------------------------------------------------------------------


def migrate_setup(setup_name: str) -> None:
    yaml_path = CONFIGS_DIR / f"{setup_name}.yaml"
    if not yaml_path.exists():
        print(f"[{setup_name}] YAML not found, skipping.")
        return

    with yaml_path.open() as f:
        raw = yaml.safe_load(f) or {}

    print(f"\n[{setup_name}]")

    # --- Water calibration ---
    csv_path = WATER_CSV.get(setup_name)
    if csv_path and csv_path.exists():
        print(f"  Water calibration: {csv_path.name}")
        cal = _water_cal_for_setup(csv_path)
        raw.setdefault("calibrations", {})["bpod_valve"] = cal
    else:
        print(f"  Water calibration: no CSV for {setup_name}, skipping.")

    # --- Stage calibration ---
    stage_path = STAGE_YAML.get(setup_name)
    if stage_path and stage_path.exists():
        print(f"  Stage calibration: {stage_path.name}")
        axes, known_pos = _stage_axes_and_positions(stage_path)
        if "stage" in raw.get("devices", {}):
            raw["devices"]["stage"]["axes"] = axes
            raw["devices"]["stage"]["known_positions"] = known_pos
        else:
            print(f"  No 'stage' device in {setup_name}, skipping stage merge.")
    else:
        print(f"  Stage calibration: no YAML for {setup_name}, skipping.")

    # --- Camera config ---
    rce_path = CAMERA_RCE.get(setup_name)
    if rce_path and rce_path.exists():
        print(f"  Camera: {rce_path}")
        raw["cameras"] = {"backend": "rce", "config": str(rce_path)}
    else:
        print(f"  Camera: no RCE config for {setup_name}, skipping.")

    with yaml_path.open("w") as f:
        yaml.dump(
            raw,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    print(f"  Written: {yaml_path}")


if __name__ == "__main__":
    for name in [
        "setup-1",
        "setup-2",
        "setup-3",
        "setup-4",
        "setup-npxb",
        "setup-npx",
    ]:
        migrate_setup(name)
    print("\nDone.")
