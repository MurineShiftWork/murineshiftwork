import logging
import os
import shutil
import sys
from pathlib import Path

from pybpodgui_api.models.project import Project

PROJECT_NAME = "main_project"
PROJECT_PATH = Path(__file__).parent.parent.parent / PROJECT_NAME


def copy_user_settings(project_name="main_project", overwrite=True):
    target = str(Path(os.path.expanduser("~")) / "user_settings.py")
    if Path(target).exists() and not overwrite:
        print("exists and cannot overwrite")
    else:
        print("found")
        from pybpod_tools.config_files import user_settings

        source = user_settings.__file__
        shutil.copyfile(source, target)

        import pybpod_tools

        DEFAULT_PROJECT_PATH = Path(pybpod_tools.__file__).parent.parent / project_name
        with open(target, "a") as f:
            f.write(f"\nDEFAULT_PROJECT_PATH = '{str(DEFAULT_PROJECT_PATH)}'\n")


def create_project():
    if not PROJECT_PATH.exists():
        PROJECT_PATH.mkdir(exist_ok=True)
        if not PROJECT_PATH.exists():
            raise FileNotFoundError(f"could not make project dir at: {PROJECT_PATH}")

        p = Project()
        p.name = PROJECT_NAME

        p.save(project_path=str(PROJECT_PATH))
        logging.debug(f"New project saved at: {PROJECT_PATH}")
    else:
        logging.debug(f"Project already exists at: {PROJECT_PATH}")


def create_tasks():
    logging.debug("TODO: implement create tassks function")
    from pkgutil import iter_modules

    def list_submodules(module):
        for submodule in iter_modules(module.__path__):
            print(submodule.name)

    import pybpod_tools.tasks as pt

    list_submodules(pt)
    # TODO: for task folder in submodules -
    #  > create new task in project and add .py file with import of this submodule/file in submodule with same name


def run_check_install():
    copy_user_settings()

    create_project()

    create_tasks()

    # create: board, setup, subject, task/protocol from tasks
    p = Project()
    p.load(project_path=PROJECT_PATH)

    # copy user settings
    # FIXME

    print(" ")
