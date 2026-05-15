import json
import logging
from pathlib import Path

import yaml

from murineshiftwork import settings as msws
from murineshiftwork.logic.config import read_config
from murineshiftwork.logic.config import validate_config_file_path
from murineshiftwork.logic.log import setup_logging
from murineshiftwork.logic.misc import find_task_by_name
from murineshiftwork.logic.misc import list_available_tasks
from murineshiftwork.logic.misc import print_box
from murineshiftwork.logic.config_io import load_setup_config
from murineshiftwork.logic.config_io import load_subject_config
from murineshiftwork.logic.config_models import ExecutionConfig
from murineshiftwork.logic.machine_config import resolve_config_dir
from murineshiftwork.logic.paths import get_host_ip
from murineshiftwork.logic.paths import get_host_name

default_out_path = str(Path.home() / "data")
default_config_dir = resolve_config_dir()
available_tasks = "\n".join([f"    - {s}" for s in list_available_tasks()])


def get_task_dir(task=None):
    exec(
        f"from murineshiftwork.tasks import {task} as task_module", globals()
    )
    exec("task_folder = Path(task_module.__file__).parent", globals())
    if "task_folder" not in globals():
        return ""
    else:
        return str(globals()["task_folder"])


def _evaluate_metadata(args_dict):
    metadata_list = args_dict.get("metadata_list", None)
    if metadata_list is not None:
        metadata_list = [
            v.strip(" ").strip("'").strip('"')
            for v in metadata_list
            if "=" in v
        ]
        metadata_dict = dict(map(lambda s: s.split("="), metadata_list))

        for metadata_key in ["researcher", "setup", "experiment"]:
            if (
                not args_dict[metadata_key].startswith("unknown_")
                or metadata_key not in metadata_dict
            ):
                # metadata_dict[f"_original__{metadata_key}"] = metadata_dict[metadata_key]
                print(metadata_key)
                metadata_dict[metadata_key] = args_dict[metadata_key]

        args_dict["metadata"] = metadata_dict
    return args_dict


def _evaluate_log_level(args_dict=None):
    # Log level
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
        args_dict["task"] = find_task_by_name(task_name=args_dict["task"])
        args_dict["task_dir"] = get_task_dir(task=args_dict["task"])
    else:
        if not args_dict["command"] == "register":
            raise ValueError(
                "Task name can only be left out if command is 'register'."
            )
        else:
            logging.debug("No task defined. Command is register.")
    return args_dict


def _evaluate_and_load_configs(args_dict=None):
    # Apply priority chain: CLI arg > env var > machine config > defaults
    config_dir = resolve_config_dir(cli_override=args_dict.get("config_dir", ""))
    args_dict["config_dir"] = config_dir
    if not Path(config_dir).exists():
        args_dict["config_dir"] = ""

    # Validate paths
    # - config files
    args_dict["config_file_subjects"] = validate_config_file_path(
        config_file=args_dict["config_file_subjects"],
        default_dir=args_dict["config_dir"],
    )
    args_dict["config_file_task"] = validate_config_file_path(
        config_file=args_dict["config_file_task"],
        default_dir=args_dict.get("task_dir", ""),
    )
    args_dict["config_file_camera"] = validate_config_file_path(
        config_file=args_dict["config_file_camera"],
        default_dir=args_dict["config_dir"],
    )
    # - calibration files
    if "calibrate" not in args_dict["task"]:
        args_dict["calibration_file_water"] = validate_config_file_path(
            config_file=args_dict["calibration_file_water"],
            default_dir=args_dict["config_dir"],
        )
        args_dict["calibration_file_sound"] = validate_config_file_path(
            config_file=args_dict["calibration_file_sound"],
            default_dir=args_dict["config_dir"],
        )
    # TODO: args_dict["serial_port_scale"]
    # TODO: args_dict["serial_port_stage"]

    # Load config/settings
    settings_subjects_all = (
        read_config(file=args_dict["config_file_subjects"])
        if args_dict["config_file_subjects"]
        else {}
    )
    settings_task_default = (
        read_config(file=args_dict["config_file_task"])
        if args_dict["config_file_task"]
        else {}
    )
    # args_dict["settings.camera"] = (
    #     read_config(file=args_dict["config_file_camera"])
    #     if args_dict["config_file_camera"]
    #     else {}
    # )
    # READ stage config
    args_dict["calibration_file_stage"] = (
        Path(args_dict["calibration_file_stage"]).expanduser().as_posix()
    )
    if Path(args_dict["calibration_file_stage"]).exists():
        args_dict["settings.stage"] = yaml.full_load(
            open(
                args_dict["calibration_file_stage"], "r"
            )  # fixme: move to yaml-config-loader AND fix for all configs to load based on file extension
        )
    else:
        args_dict["settings.stage"] = {}

    # add to args
    args_dict["settings.subjects.all"] = settings_subjects_all
    args_dict["settings.task.default"] = settings_task_default

    # Load new-style configs — silent no-op if YAML files absent, old flag path continues
    args_dict["setup_config"] = load_setup_config(
        config_dir=args_dict["config_dir"],
        setup_name=args_dict.get("setup", ""),
    )
    args_dict["subject_config"] = load_subject_config(
        config_dir=args_dict["config_dir"],
        subject_name=args_dict.get("subject", ""),
    )

    return args_dict


def evaluate_args(args_dict=None):
    """Evaluate parsed arguments.

    :param args_dict: output of parser
    :return:
    """
    # Add other metadata
    args_dict["host_name"] = get_host_name()
    args_dict["host_ip"] = get_host_ip()

    # Back up original values
    args_dict["original"] = args_dict.copy()

    args_dict = _evaluate_log_level(args_dict=args_dict)
    setup_logging(level=args_dict["log_level"], log_file=args_dict["log_file"])

    args_dict = _evaluate_task(args_dict=args_dict)
    args_dict = _evaluate_metadata(args_dict=args_dict)

    args_dict = _evaluate_and_load_configs(args_dict=args_dict)

    # TODO: refactor settings patching
    settings_subjects_all = args_dict["settings.subjects.all"]
    settings_task_default = args_dict["settings.task.default"]

    if args_dict["command"] == "register":
        pass
    elif args_dict["command"] == "run":
        subject = args_dict["subject"]
        subject_config = args_dict.get("subject_config")
        in_ini = subject in settings_subjects_all
        in_yaml = subject_config is not None

        if not in_ini and not in_yaml:
            if args_dict["debug"]:
                args_dict["subject"] = "_test_subject"
                logging.debug("Overwriting subject to _test_subject for debug mode")
            else:
                raise ValueError(
                    f"\n\n\tUnknown subject '{subject}'. Not found in subject.settings nor in "
                    f"{args_dict['config_dir']}/subjects/. "
                    f"Register first: murineshiftwork register add -s {subject}\n"
                )
    else:
        raise ValueError(f"Unknown command: '{args_dict['command']}'")

    # Build settings.task.patched — priority (lowest → highest):
    #   1. task.settings INI defaults
    #   2. subject INI task-specific overrides
    #   3. SubjectConfig.task_overrides (YAML)
    #   4. CLI --task-settings KEY=VALUE

    patched = dict(settings_task_default)
    task_name = args_dict.get("task", "")

    # Layer 2: INI subject overrides
    settings_subjects_this = settings_subjects_all.get(args_dict["subject"], None)
    if settings_subjects_this:
        task_patch_ini = settings_subjects_this.get(task_name, {})
        patched.update(task_patch_ini)
        for k, v in settings_subjects_this.items():
            if k != task_name and not isinstance(v, dict):
                args_dict.setdefault("subject.metadata", {})[k] = v

    # Layer 3: YAML SubjectConfig.task_overrides
    subject_config = args_dict.get("subject_config")
    if subject_config and task_name in subject_config.task_overrides:
        yaml_patch = subject_config.task_overrides[task_name]
        patched.update(yaml_patch)
        logging.debug(
            f"Subject YAML task_overrides for '{task_name}': {yaml_patch}"
        )

    # Layer 4: CLI --task-settings KEY=VALUE overrides
    cli_overrides = _parse_key_value_list(
        args_dict.get("task_settings_overrides", [])
    )
    patched.update(cli_overrides)

    if cli_overrides:
        logging.debug(f"CLI task-settings overrides applied: {cli_overrides}")

    if patched:
        txt = json.dumps(patched, indent=4, sort_keys=True, default=str)
        logging.debug(f"settings.task.patched for '{task_name}':\n{txt}")

    # Inject CLI-level calibration file paths as lowest-priority defaults in patched settings
    # Tasks read from settings.task.patched; override via -ts calibration_file_water=/path
    for _cal_key in ("calibration_file_water", "calibration_file_sound", "calibration_file_stage"):
        if _cal_key in args_dict and _cal_key not in patched:
            patched[_cal_key] = args_dict[_cal_key]

    args_dict["settings.task.patched"] = patched

    # Resolve bpod serial port from SetupConfig when available
    setup_config = args_dict.get("setup_config")
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

    # Resolve camera config from SetupConfig when available and CLI path is absent/invalid
    if setup_config and setup_config.cameras:
        cam_path = setup_config.cameras.get("config", "")
        if cam_path and (not args_dict.get("config_file_camera") or
                         not Path(args_dict.get("config_file_camera", "")).exists()):
            args_dict["config_file_camera"] = cam_path
            logging.debug(f"Resolved camera config from SetupConfig: {cam_path}")

    args_dict["execution_config"] = ExecutionConfig(
        setup=setup_config,
        subject=subject_config,
        task_name=task_name,
        task_settings=patched,
    )

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
