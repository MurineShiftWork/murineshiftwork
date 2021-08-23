import json
import logging
from pathlib import Path

from murine_shift_work import settings as msws
from murine_shift_work.logic.config import read_config
from murine_shift_work.logic.config import setup_logging
from murine_shift_work.logic.misc import find_task_by_name
from murine_shift_work.logic.misc import list_available_tasks

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


def validate_config_file_path(
    config_file=None,
    default_dir=None,
):
    config_file = Path(config_file)
    if config_file.exists():
        logging.debug(f"Found config file: {str(config_file)}")
        return str(config_file)
    else:
        if len(config_file.parts) == 1:
            default_dir = Path(default_dir)
            if (default_dir / config_file).exists():
                logging.debug(f"Found config file: {str(default_dir / config_file)}")
                return str(default_dir / config_file)
            else:
                logging.debug(
                    f"(1) File '{str(config_file)}' does not exist on its own or in default location at '{str(default_dir)}'"
                )
                return ""
        else:
            logging.debug(
                f"(2) File '{str(config_file)}' does not exist on its own or in default location at '{str(default_dir)}'"
            )
            return ""


def evaluate_args(args_dict=None):
    """

    :param args_dict:
    :return:
    """
    args_dict["original"] = args_dict.copy()

    # Log level
    if args_dict["debug"]:
        args_dict["log_level"] = "DEBUG"
    try:
        d_int = int(args_dict["log_level"])
        args_dict["log_int"] = d_int
        args_dict["log_level"] = logging.getLevelName(d_int)
    except ValueError:
        pass

    setup_logging(level=args_dict["log_level"])

    # Task name
    if args_dict["task"]:
        args_dict["task"] = find_task_by_name(task_name=args_dict["task"])
        args_dict["task_dir"] = get_task_dir(task=args_dict["task"])
    else:
        if not args_dict["command"] == "register":
            raise ValueError("Task name can only be left out if command is 'register'.")
        else:
            logging.debug("No task defined. Command is register.")

    # Config files
    config_dir = args_dict["config_dir"]
    if not Path(config_dir).exists():
        args_dict["config_dir"] = ""

    # Validate paths
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
    if args_dict["debug"]:
        args_dict["settings.subjects.all"] = settings_subjects_all
        args_dict["settings.task.default"] = settings_task_default

    if args_dict["command"] == "register":

        pass  # TODO: add parser option for --move-data
        # TODO: add check to execute.register for subcommands

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

        txt = json.dumps(args_dict["settings.subjects.this"], indent=4, sort_keys=True)
        logging.debug(
            f"Settings overwrite for subject '{args_dict['subject']}':\n{txt}"
        )

    return args_dict
