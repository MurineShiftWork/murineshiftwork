import json
import logging
from pathlib import Path

from murine_shift_work import settings as msws
from murine_shift_work.logic.config import read_config
from murine_shift_work.logic.config import validate_config_file_path
from murine_shift_work.logic.log import setup_logging
from murine_shift_work.logic.misc import find_task_by_name
from murine_shift_work.logic.misc import list_available_tasks
from murine_shift_work.logic.misc import print_box
from murine_shift_work.logic.paths import get_host_ip
from murine_shift_work.logic.paths import get_host_name

default_out_path = str(Path.home() / "data")
default_config_dir = str(msws.__path__[0])
available_tasks = "\n".join([f"    - {s}" for s in list_available_tasks()])


def get_task_dir(task=None):
    exec(f"from murine_shift_work.tasks import {task} as task_module", globals())
    exec("task_folder = Path(task_module.__file__).parent", globals())
    if "task_folder" not in globals():
        return ""
    else:
        return str(globals()["task_folder"])


def _evaluate_metadata(args_dict):
    metadata_list = args_dict.get("metadata_list", None)
    if metadata_list is not None:
        metadata_list = [
            v.strip(" ").strip("'").strip('"') for v in metadata_list if "=" in v
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
            raise ValueError("Task name can only be left out if command is 'register'.")
        else:
            logging.debug("No task defined. Command is register.")
    return args_dict


def _evaluate_and_load_configs(args_dict=None):
    config_dir = args_dict["config_dir"]
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
    # args_dict["serial_port_scale"]  TODO

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
    args_dict["settings.camera"] = (
        read_config(file=args_dict["config_file_camera"])
        if args_dict["config_file_camera"]
        else {}
    )
    args_dict["settings.subjects.all"] = settings_subjects_all
    args_dict["settings.task.default"] = settings_task_default

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
        pass  # fixme: Do anything ?
    elif args_dict["command"] == "run":
        # Subject has to EXIST via `register`
        if not args_dict["subject"] in settings_subjects_all.keys():
            if args_dict["debug"]:
                args_dict["subject"] = "_test_subject"
                logging.debug("Overwriting subject for testing")
            else:
                raise ValueError(
                    f"\n\n\tUnknown subject '{args_dict['subject']}'. Check if typo in name -or- "
                    f"register new subjects first with: murineshiftwork register add -s SUBJECT -t TASK\n"
                )
    else:
        raise ValueError(f"Unknown command: '{args_dict['command']}'")

    # Patch task settings with specific subject settings if available
    args_dict["settings.task.patched"] = settings_task_default
    settings_subjects_this = settings_subjects_all.get(args_dict["subject"], None)

    if settings_subjects_this:
        task_settings_patch = settings_subjects_this.get(args_dict["task"], None)
        if task_settings_patch:
            args_dict["settings.subjects.this"] = task_settings_patch
            for k, v in task_settings_patch.items():
                # if k in arg_dict["task.settings.patched"]
                args_dict["settings.task.patched"][k] = v

            for k, v in settings_subjects_this.items():
                if not k == args_dict["task"] and not isinstance(v, dict):
                    if "subject.metadata" not in args_dict.keys():
                        args_dict["subject.metadata"] = {}
                    args_dict["subject.metadata"][k] = v

            txt = json.dumps(task_settings_patch, indent=4, sort_keys=True)
            logging.debug(
                f"Settings overwrite for subject '{args_dict['subject']}':\n{txt}"
            )
    else:
        if not args_dict["command"] == "register":
            print_box(
                f"No subject settings found for '{args_dict['subject']}'.\n"
                f"Check that subject is registered"
            )
            args_dict["exit_flag"] = True

    return args_dict
