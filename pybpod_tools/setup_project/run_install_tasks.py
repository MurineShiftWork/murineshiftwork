import logging
import shutil
import sys
from pathlib import Path

from pybpodgui_api.models.project import Project

PROJECT_NAME = "main_project"
PROJECT_PATH = Path(__file__).parent.parent.parent / PROJECT_NAME


def copy_user_settings():
    pass


def create_project():
    if not PROJECT_PATH.exists():
        PROJECT_PATH.mkdir(exist_ok=True)
        if not PROJECT_PATH.exists():
            raise FileNotFoundError(f"could not make project dir at: {PROJECT_PATH}")

        p = Project()
        p.name = PROJECT_NAME

        p.save(project_path=str(PROJECT_PATH))
        logging.info(f"New project saved at: {PROJECT_PATH}")
    else:
        logging.info(f"Project already exists at: {PROJECT_PATH}")


def run_check_install():
    copy_user_settings()

    create_project()

    # create: board, setup, subject, task/protocol from tasks
    p = Project()
    p.load(project_path=PROJECT_PATH)

    # copy user settings
    # FIXME

    print(" ")
