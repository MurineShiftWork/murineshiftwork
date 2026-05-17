import json
import logging
from pathlib import Path

import yaml

from murineshiftwork.cli.defaults import (
    DEFAULT_CALIBRATION_FILE_SOUND,
    DEFAULT_CALIBRATION_FILE_STAGE,
    DEFAULT_CALIBRATION_FILE_WATER,
    available_tasks,
    default_config_dir,
    default_out_path,
)
from murineshiftwork.cli.preflight import preflight_hardware_check
from murineshiftwork.logic.config import (
    ExecutionConfig,
    load_setup_config,
    load_subject_config,
    read_config,
    read_task_modes,
    validate_config_file_path,
)
from murineshiftwork.logic.log import setup_logging
from murineshiftwork.logic.machine_config import resolve_config_dir
from murineshiftwork.logic.misc import find_task_by_name
from murineshiftwork.logic.paths import get_host_ip, get_host_name

# Re-export for anything that imported these from here before the split
__all__ = [
    "evaluate_args",
    "get_task_dir",
    "available_tasks",
    "default_config_dir",
    "default_out_path",
]


def get_task_dir(task=None):
    import importlib

    try:
        mod = importlib.import_module(f"murineshiftwork.tasks.{task}.{task}")
        return str(Path(mod.__file__).parent)
    except (ImportError, AttributeError):
        return ""


def _evaluate_metadata(args_dict):
    metadata_dict = {}
    # Key=value pairs from --meta
    metadata_list = args_dict.get("metadata_list", None)
    if metadata_list:
        kv_list = [v.strip().strip("'\"") for v in metadata_list if "=" in v]
        metadata_dict.update(dict(s.split("=", 1) for s in kv_list))
    # Named convenience args override --meta
    if args_dict.get("setup"):
        metadata_dict["setup"] = args_dict["setup"]
    if args_dict.get("experimenter"):
        metadata_dict["experimenter"] = args_dict["experimenter"]
    args_dict["metadata"] = metadata_dict
    return args_dict


def _evaluate_log_level(args_dict=None):
    if args_dict["debug"]:
        args_dict["log_level"] = "DEBUG"
    try:
        d_int = int(args_dict["log_level"])
        args_dict["log_int"] = d_int
        args_dict["log_level"] = logging.getLevelName(d_int)
    except ValueError:
        pass
    return args_dict


def _evaluate_task(args_dict=None):
    if args_dict["task"]:
        requested = args_dict["task"]
        args_dict["task"] = find_task_by_name(task_name=requested)
        if args_dict["task"] is None:
            from murineshiftwork.logic.misc import list_available_tasks

            raise ValueError(
                f"Unknown task '{requested}'. Available tasks:\n"
                + "\n".join(f"  {t}" for t in sorted(list_available_tasks()))
            )
        args_dict["task_dir"] = get_task_dir(task=args_dict["task"])
    else:
        raise ValueError(
            "Task name is required. Pass -t <task_name> to the run command."
        )
    return args_dict


def _evaluate_and_load_configs(args_dict=None):
    # Apply priority chain: CLI arg > env var > machine config > defaults
    config_dir = resolve_config_dir(cli_override=args_dict.get("config_dir", ""))
    args_dict["config_dir"] = config_dir
    if not Path(config_dir).exists():
        args_dict["config_dir"] = ""

    args_dict["config_file_subjects"] = validate_config_file_path(
        config_file=args_dict.get("config_file_subjects", ""),
        default_dir=args_dict["config_dir"],
    )
    args_dict["config_file_task"] = validate_config_file_path(
        config_file=args_dict.get("config_file_task", "task.yaml"),
        default_dir=args_dict.get("task_dir", ""),
    )
    args_dict["config_file_camera"] = validate_config_file_path(
        config_file=args_dict.get("config_file_camera", ""),
        default_dir=args_dict["config_dir"],
    )
    if not args_dict["task"].startswith("_calibration"):
        args_dict["calibration_file_water"] = validate_config_file_path(
            config_file=args_dict.get(
                "calibration_file_water", DEFAULT_CALIBRATION_FILE_WATER
            ),
            default_dir=args_dict["config_dir"],
        )
        args_dict["calibration_file_sound"] = validate_config_file_path(
            config_file=args_dict.get(
                "calibration_file_sound", DEFAULT_CALIBRATION_FILE_SOUND
            ),
            default_dir=args_dict["config_dir"],
        )

    settings_task_default = (
        read_config(file=args_dict["config_file_task"])
        if args_dict["config_file_task"]
        else {}
    )

    calibration_file_stage = args_dict.get(
        "calibration_file_stage", DEFAULT_CALIBRATION_FILE_STAGE
    )
    args_dict["calibration_file_stage"] = (
        Path(calibration_file_stage).expanduser().as_posix()
    )
    if Path(args_dict["calibration_file_stage"]).exists():
        with open(args_dict["calibration_file_stage"], "r") as _f:
            args_dict["settings.stage"] = yaml.full_load(_f)
    else:
        args_dict["settings.stage"] = {}

    args_dict["settings.task.default"] = settings_task_default

    args_dict["setup_config"] = load_setup_config(
        config_dir=args_dict["config_dir"],
        setup_name=args_dict.get("setup", ""),
    )
    args_dict["subject_config"] = load_subject_config(
        config_dir=args_dict["config_dir"],
        subject_name=args_dict.get("subject", ""),
    )

    return args_dict


def _stage_device_to_controller_config(device) -> dict:
    """Convert a StageTowerDevice to the dict format StageController.from_config() expects."""
    return {
        "connection": {
            "baudrate": device.baudrate,
            "timeout": device.timeout,
        },
        "axes": {
            name: {
                "id": ax.id,
                "position_min": ax.position_min,
                "position_max": ax.position_max,
                "velocity_max": ax.velocity_max,
                "operating_mode": ax.operating_mode,
            }
            for name, ax in device.axes.items()
        },
        "known_positions": device.known_positions,
    }


def _build_task_settings_patch(args_dict, settings_task_default, task_modes):
    """Build settings.task.patched from the 4-level priority chain."""
    patched = dict(settings_task_default)
    task_name = args_dict.get("task", "")

    task_mode = args_dict.get("task_mode", "")
    if task_mode:
        if task_mode not in task_modes:
            raise ValueError(
                f"Task mode '{task_mode}' not found in task.yaml 'mode:' section. "
                f"Available: {list(task_modes.keys())}"
            )
        mode_overrides = task_modes[task_mode]
        patched.update(mode_overrides)
        logging.debug(f"Task mode '{task_mode}' applied: {mode_overrides}")

    subject_config = args_dict.get("subject_config")
    if subject_config and task_name in subject_config.task_overrides:
        yaml_patch = subject_config.task_overrides[task_name]
        patched.update(yaml_patch)
        logging.debug(f"Subject YAML task_overrides for '{task_name}': {yaml_patch}")

    cli_overrides = _parse_key_value_list(args_dict.get("task_settings_overrides", []))
    patched.update(cli_overrides)
    if cli_overrides:
        logging.debug(f"CLI task-settings overrides applied: {cli_overrides}")

    if patched:
        logging.debug(
            f"settings.task.patched for '{task_name}':\n"
            + json.dumps(patched, indent=4, sort_keys=True, default=str)
        )

    for _cal_key in (
        "calibration_file_water",
        "calibration_file_sound",
        "calibration_file_stage",
        "serial_port_stage",
        "serial_port_pulsepal",
        "serial_port_scale",
    ):
        if _cal_key in args_dict and _cal_key not in patched:
            patched[_cal_key] = args_dict[_cal_key]
    if "settings.stage" in args_dict and "settings.stage" not in patched:
        patched["settings.stage"] = args_dict["settings.stage"]

    return patched


def _resolve_setup_config_ports(args_dict, setup_config, patched):
    """Apply port and camera overrides from SetupConfig into args_dict and patched."""
    if setup_config and "bpod" in setup_config.devices:
        try:
            resolved = setup_config.device_port("bpod")
            args_dict["serial_port_bpod"] = resolved
            logging.debug(f"Resolved bpod port from SetupConfig: {resolved}")
        except ValueError as exc:
            logging.warning(
                f"SetupConfig bpod port resolution failed ({exc}); "
                f"using CLI value {args_dict['serial_port_bpod']!r}"
            )

    if setup_config and "stage" in setup_config.devices:
        stage_dev = setup_config.devices["stage"]
        try:
            resolved_stage = setup_config.device_port("stage")
            args_dict["serial_port_stage"] = resolved_stage
            patched["serial_port_stage"] = resolved_stage
            logging.debug(f"Resolved stage port from SetupConfig: {resolved_stage}")
        except ValueError as exc:
            logging.warning(f"SetupConfig stage port resolution failed ({exc})")
        # Always prefer setup config axes over old calibration files
        args_dict["settings.stage"] = _stage_device_to_controller_config(stage_dev)
        patched["settings.stage"] = args_dict["settings.stage"]
        logging.debug("Built settings.stage from SetupConfig stage device")

    if setup_config and setup_config.cameras:
        cam_path = setup_config.cameras.config
        if cam_path and (
            not args_dict.get("config_file_camera")
            or not Path(args_dict.get("config_file_camera", "")).exists()
        ):
            args_dict["config_file_camera"] = cam_path
            logging.debug(f"Resolved camera config from SetupConfig: {cam_path}")


def evaluate_args(args_dict=None):
    """Evaluate parsed arguments."""
    args_dict["host_name"] = get_host_name()
    args_dict["host_ip"] = get_host_ip()
    args_dict["original"] = args_dict.copy()

    args_dict = _evaluate_log_level(args_dict=args_dict)
    setup_logging(level=args_dict["log_level"], log_file=args_dict["log_file"])

    args_dict = _evaluate_task(args_dict=args_dict)
    args_dict = _evaluate_metadata(args_dict=args_dict)
    args_dict = _evaluate_and_load_configs(args_dict=args_dict)

    settings_task_default = args_dict["settings.task.default"]
    task_modes = read_task_modes(args_dict.get("config_file_task", ""))

    if args_dict["command"] == "run":
        subject = args_dict["subject"]
        subject_config = args_dict.get("subject_config")
        if subject_config is None and subject != "_test_subject":
            if args_dict["debug"]:
                args_dict["subject"] = "_test_subject"
                logging.debug("Overwriting subject to _test_subject for debug mode")
            else:
                raise ValueError(
                    f"\n\n\tUnknown subject '{subject}'. Not found in "
                    f"{args_dict['config_dir']}/subjects/. "
                    f"Register first: murineshiftwork subject add -s {subject}\n"
                )
    else:
        raise ValueError(f"Unknown command: '{args_dict['command']}'")

    patched = _build_task_settings_patch(args_dict, settings_task_default, task_modes)
    args_dict["settings.task.patched"] = patched

    setup_config = args_dict.get("setup_config")
    _resolve_setup_config_ports(args_dict, setup_config, patched)

    task_name = args_dict.get("task", "")
    subject_config = args_dict.get("subject_config")
    args_dict["execution_config"] = ExecutionConfig(
        setup=setup_config,
        subject=subject_config,
        task_name=task_name,
        task_settings=patched,
    )

    if args_dict.get("command") == "run":
        preflight_hardware_check(args_dict)

    return args_dict


def _parse_key_value_list(kv_list: list) -> dict:
    """Parse ['KEY=VALUE', ...] into a dict with type coercion."""
    import ast

    result = {}
    for item in kv_list:
        item = item.strip().strip("'\"")
        if "=" not in item:
            continue
        k, _, v = item.partition("=")
        k = k.strip()
        v = v.strip()
        try:
            result[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            result[k] = v
    return result
