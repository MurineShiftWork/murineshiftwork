from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from murineshiftwork.logic.config.models import SetupConfig, SubjectConfig, ValveCalibration


def load_setup_config(config_dir: str | Path, setup_name: str) -> Optional[SetupConfig]:
    """Load SetupConfig from {config_dir}/setups/{setup_name}.yaml.

    Returns None silently if the file does not exist, so callers fall through
    to the existing flat-flag path without any change in behaviour.
    """
    if not setup_name or setup_name.startswith("unknown_"):
        return None
    path = Path(config_dir) / "setups" / f"{setup_name}.yaml"
    if not path.exists():
        logging.warning(f"Setup '{setup_name}' not found at {path} — bpod port from CLI arg only")
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    cfg = SetupConfig.model_validate(data)
    logging.debug(f"Loaded SetupConfig '{cfg.name}' from {path}")
    return cfg


def update_valve_calibration(
    config_dir: str | Path,
    setup_name: str,
    valve_id: int | str,
    new_calibration: ValveCalibration,
    force: bool = False,
) -> bool:
    """Write new_calibration for one valve into {config_dir}/setups/{setup_name}.yaml.

    Only the specific valve entry is replaced; all other setup fields are preserved
    verbatim (comments are lost on round-trip through yaml.dump, but structure is kept).

    Validation is run before writing unless force=True.  Returns True if the file
    was written, False if validation failed and force=False.

    Raises FileNotFoundError if the setup YAML does not exist yet (create it first
    or run `murineshiftwork register` for the setup).
    """
    path = Path(config_dir) / "setups" / f"{setup_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Setup config not found: {path}\n"
            f"Create the file first or run: murineshiftwork register --setup {setup_name}"
        )

    is_valid, reason = new_calibration.validate()
    if not is_valid:
        if force:
            logging.warning(
                f"Calibration for valve {valve_id} failed validation ({reason}) — "
                f"writing anyway because force=True"
            )
        else:
            logging.error(
                f"Calibration for valve {valve_id} failed validation: {reason}. "
                f"Not writing to {path}. Pass force=True to override."
            )
            return False

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    raw.setdefault("calibrations", {}).setdefault("bpod_valve", {})[str(valve_id)] = {
        "updated": new_calibration.updated,
        "points": new_calibration.points,
    }

    with open(path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logging.info(
        f"Wrote calibration for valve {valve_id} of setup '{setup_name}' "
        f"({len(new_calibration.points)} points, updated {new_calibration.updated})"
    )
    return True


def save_subject_task_stage_position(
    config_dir: str | Path,
    subject_name: str,
    task_name: str,
    position_name: str,
) -> None:
    """Write stage_position into subject's task_overrides for the given task.

    Creates the subjects YAML file if it doesn't exist.
    Merges into existing task_overrides without overwriting other keys.
    """
    subjects_dir = Path(config_dir) / "subjects"
    subjects_dir.mkdir(parents=True, exist_ok=True)
    path = subjects_dir / f"{subject_name}.yaml"

    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {
            "name": subject_name,
            "registered": "",
            "project": "",
            "experiment": "",
            "comment": "",
            "aliases": [],
            "task_overrides": {},
        }

    raw.setdefault("task_overrides", {}).setdefault(task_name, {})["stage_position"] = position_name

    with open(path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logging.info(
        f"Saved stage_position '{position_name}' for subject '{subject_name}', task '{task_name}' → {path}"
    )


def update_stage_config(
    config_dir: str | Path,
    setup_name: str,
    stage_controller_config: dict,
) -> bool:
    """Write updated axis limits and known_positions from a StageController config back to the setup YAML.

    Only axis limits (position_min, position_max, velocity_max, operating_mode) and
    known_positions are written — position_raw is transient hardware state and is skipped.
    Returns True if the file was written.
    """
    path = Path(config_dir) / "setups" / f"{setup_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Setup config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    stage = raw.setdefault("devices", {}).setdefault("stage", {})

    for axis_name, axis_data in stage_controller_config.get("axes", {}).items():
        axis = stage.setdefault("axes", {}).setdefault(axis_name, {})
        for key in ("position_min", "position_max", "velocity_max", "operating_mode"):
            if key in axis_data:
                axis[key] = axis_data[key]

    known_positions = stage_controller_config.get("known_positions", {})
    if known_positions:
        stage["known_positions"] = known_positions

    with open(path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logging.info(f"Updated stage config in setup '{setup_name}' at {path}")
    return True


def load_subject_config(config_dir: str | Path, subject_name: str) -> Optional[SubjectConfig]:
    """Load SubjectConfig from {config_dir}/subjects/{subject_name}.yaml.

    Returns None silently if the file does not exist; INI-based subject
    loading in evaluate.py is the fallback.
    """
    if not subject_name or subject_name.startswith("_test_"):
        return None
    path = Path(config_dir) / "subjects" / f"{subject_name}.yaml"
    if not path.exists():
        logging.debug(f"No subject config at {path} — using INI fallback")
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    cfg = SubjectConfig.model_validate(data)
    logging.debug(f"Loaded SubjectConfig '{cfg.name}' from {path}")
    return cfg
