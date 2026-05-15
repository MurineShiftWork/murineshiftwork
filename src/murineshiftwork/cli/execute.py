import json
import logging
from pathlib import Path

import yaml

from murineshiftwork.logic.config import write_config
from murineshiftwork.logic.machine_config import (
    get_machine_config_path,
    read_machine_config,
    resolve_config_dir,
    write_machine_config,
)
from murineshiftwork.logic.misc import print_box


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
            write_config(
                in_dict=updated_settings, save_path=config_file_subjects
            )
            print_box(f"Added subject '{subject}' to subject.settings.")
        else:
            print_box(
                f"Subject '{subject}' already exists with settings:\n"
                f"{json.dumps(args_dict['settings.subjects.all'][subject], indent=4, sort_keys=True)}"
            )

    elif "remove" in option:
        if subject in subject_settings_all:
            subject_settings_all.pop(subject)

            write_config(
                in_dict=subject_settings_all, save_path=config_file_subjects
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
            write_config(
                in_dict=subject_settings_all, save_path=config_file_subjects
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
                        print_box(
                            f"Moved subject '{subject}' data to {str(new)}."
                        )
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
        f"from murineshiftwork.tasks.{task_name}.{task_name} import run_task",
        globals(),
    )
    run_task(**args_dict)
    logging.debug("Task finished.")


# ---------------------------------------------------------------------------
# murineshiftwork init

def run_init(**args_dict):
    """Write ~/.murineshiftwork/msw_machine.yaml with the given config_dir.

    Also creates the config_dir directory structure if it does not exist.
    """
    config_dir = Path(args_dict["config_dir"]).expanduser().resolve()

    # Create directory tree
    for sub in ("setups", "subjects", "tasks", "device_configs/cameras"):
        (config_dir / sub).mkdir(parents=True, exist_ok=True)

    write_machine_config(config_dir)

    print_box(
        f"Initialised MSW on this machine.\n"
        f"Config dir: {config_dir}\n"
        f"Machine config: {get_machine_config_path()}\n\n"
        f"Next steps:\n"
        f"  murineshiftwork setup create <setup_name>\n"
        f"  murineshiftwork subject add -s <subject_name>"
    )


# ---------------------------------------------------------------------------
# murineshiftwork setup

def run_setup(**args_dict):
    """Create or show setup configs."""
    subcommand = args_dict["subcommand"]
    config_dir = Path(resolve_config_dir(args_dict.get("config_dir", "")))
    setups_dir = config_dir / "setups"

    if subcommand == "create":
        setup_name = args_dict["setup_name"]
        path = setups_dir / f"{setup_name}.yaml"
        if path.exists() and not args_dict.get("force", False):
            print_box(
                f"Setup '{setup_name}' already exists at {path}.\n"
                f"Use --force to overwrite."
            )
            return

        setups_dir.mkdir(parents=True, exist_ok=True)
        skeleton = {
            "name": setup_name,
            "devices": {
                "bpod": {"type": "bpod", "port_by_path": "FILL_IN_PORT_BY_PATH"},
            },
            "calibrations": {"bpod_valve": {}},
        }
        with open(path, "w") as f:
            yaml.dump(skeleton, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print_box(f"Created setup config skeleton: {path}\nEdit the file to fill in device port_by_path values.")

    elif subcommand == "list":
        if not setups_dir.exists():
            print_box(f"No setups dir at {setups_dir}")
            return
        filt = args_dict.get("filter", "").lower()
        setups = sorted(p.stem for p in setups_dir.glob("*.yaml"))
        if filt:
            setups = [s for s in setups if filt in s.lower()]
        print_box(f"Available setups in {setups_dir}:\n" + "\n".join(f"  - {s}" for s in setups))

    else:
        raise ValueError(f"Unknown setup subcommand: {subcommand!r}")


# ---------------------------------------------------------------------------
# murineshiftwork subject

def run_subject(**args_dict):
    """Add or list YAML-based subjects."""
    subcommand = args_dict["subcommand"]
    config_dir = Path(resolve_config_dir(args_dict.get("config_dir", "")))
    subjects_dir = config_dir / "subjects"
    subjects_dir.mkdir(parents=True, exist_ok=True)

    if subcommand == "add":
        subject_name = args_dict["subject"]
        path = subjects_dir / f"{subject_name}.yaml"
        if path.exists() and not args_dict.get("force", False):
            print_box(f"Subject '{subject_name}' already exists at {path}.")
            return

        data = {
            "name": subject_name,
            "registered": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "project": args_dict.get("project", ""),
            "experiment": args_dict.get("experiment", ""),
            "comment": args_dict.get("comment", ""),
            "aliases": [],
            "task_overrides": {},
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print_box(f"Registered subject '{subject_name}' at {path}")

    elif subcommand == "list":
        filt = args_dict.get("filter", "").lower()
        subjects = sorted(p.stem for p in subjects_dir.glob("*.yaml"))
        if filt:
            subjects = [s for s in subjects if filt in s.lower()]
        print_box(
            f"Registered subjects ({len(subjects)}) in {subjects_dir}:\n"
            + "\n".join(f"  - {s}" for s in subjects)
        )

    else:
        raise ValueError(f"Unknown subject subcommand: {subcommand!r}")
