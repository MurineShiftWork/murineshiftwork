import json
import logging
from pathlib import Path

from murine_shift_work.logic.config import update_config_file
from murine_shift_work.logic.misc import print_box


def run_register(**args_dict):
    """ """
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
            if args_dict.get("task", ""):
                new_dict = {args_dict.get("task"): {}}
            else:
                new_dict = {}

            updated_settings[args_dict["subject"]] = new_dict
            update_config_file(in_dict=updated_settings, out_file=config_file_subjects)
            print_box(f"Added subject '{subject}' to subject.settings.")
        else:
            print_box(
                f"Subject '{subject}' already exists with settings:\n"
                f"{json.dumps(args_dict['settings.subjects.all'][subject], indent=4, sort_keys=True)}"
            )

    elif "remove" in option:
        if subject in subject_settings_all:
            subject_settings_all.pop(subject)

            update_config_file(
                in_dict=subject_settings_all, out_file=config_file_subjects
            )
            print_box(f"Removed subject '{subject}' from subject.settings.")
        else:
            print_box(f"Subject '{subject}' does NOT exist.")

    elif "rename" in option:
        if subject in subject_settings_all.keys():

            new_alias = args_dict["new_alias"]
            if new_alias in subject_settings_all.keys():
                print_box(
                    f"New subject alias '{new_alias}' already exists. Cannot rename subject '{subject}'."
                )
                return

            subject_settings_all[new_alias] = subject_settings_all.pop(subject)
            update_config_file(
                in_dict=subject_settings_all, out_file=config_file_subjects
            )
            print_box(
                f"Renamed subject '{subject}' to '{new_alias}' in subject.settings."
            )

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
                        print_box(f"Moved subject '{subject}' data to {str(new)}.")
                else:
                    print_box(f"No data to move for subject '{subject}'.")
        else:
            print_box(f"Subject '{subject}' does NOT exist.")

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
