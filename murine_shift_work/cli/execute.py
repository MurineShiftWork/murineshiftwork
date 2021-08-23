import logging
from pathlib import Path
from shutil import copyfile

from configobj import ConfigObj


def _update_config_file(in_dict=None, out_file=None, backup_extension="bak"):
    new_config = ConfigObj(in_dict)
    dst = ".".join([str(out_file), backup_extension])
    copyfile(src=out_file, dst=dst)
    if not Path(dst).exists():
        raise FileNotFoundError("we made it, but doesn't exist!")

    new_config.filename = out_file
    new_config.write()

    if not Path(new_config.filename).exists():
        raise FileNotFoundError("")


def run_register(**args_dict):
    """"""
    option = args_dict["subcommand"]
    subject = args_dict["subject"]
    subject_settings_all = args_dict["settings.subjects.all"]
    config_file_subjects = args_dict["config_file_subjects"]
    data_folder = Path(args_dict["out_path"])

    if "add" in option:
        if (
            not args_dict["subject"] in args_dict["settings.subjects.all"]
            and Path(args_dict["config_file_subjects"]).exists()
        ):
            updated_settings = args_dict["settings.subjects.all"]
            updated_settings[args_dict["subject"]] = {args_dict.get("task", ""): {}}

            _update_config_file(in_dict=updated_settings, out_file=config_file_subjects)
        else:
            pass  # FIXME: warn that exists

    elif "remove" in option:
        if subject in subject_settings_all:
            subject_settings_all.pop(subject)

            _update_config_file(
                in_dict=subject_settings_all, out_file=config_file_subjects
            )
        else:
            pass  # FIXME: inform if does not exist

    elif "move" in option:
        if subject in subject_settings_all.keys():

            new_alias = args_dict["new_alias"]
            if new_alias in subject_settings_all.keys():
                raise ValueError(
                    f"New alias exists already: {new_alias}. Choose a different one."
                )

            subject_settings_all[new_alias] = subject_settings_all.pop(subject)

            if args_dict["move_data"]:
                old = data_folder / subject
                new = data_folder / new_alias
                if old.exists():
                    old.rename(new)
                    if not new.exists():
                        raise FileNotFoundError(
                            f"Cannot see new folder {str(new)}, but old one does {'' if old.exists() else 'NOT'} exists at {str(old)}"
                        )
        else:
            pass  # FIXME: warn that subject does not exists in the first place

    else:
        raise ValueError(f"Unknown option '{option}'")

    logging.debug("Registration operations completed.")


def run_task(**args_dict):
    """
    msw run -s subject -t task
    msw run -s subject -t task -p serial_port

    """
    task_name = args_dict["task"]
    exec(
        f"from murine_shift_work.tasks.{task_name}.{task_name} import run_task",
        globals(),
    )
    run_task(**args_dict)
    logging.debug("Task finished.")
