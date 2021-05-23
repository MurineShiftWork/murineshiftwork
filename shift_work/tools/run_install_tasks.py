import logging
import os
import shutil
import time
from pathlib import Path

import git
from pybpodgui_api.models.project import Project

import shift_work
import shift_work.tasks as module_tasks
from shift_work.config_files import install_settings
from shift_work.config_files import user_settings
from shift_work.tools.misc import list_submodules


def get_package_dir():
    """First parent is code folder, second is enclosing .git repo."""
    return Path(shift_work.__file__).parent.parent


PROJECT_NAME = "main_project"
PROJECT_PATH = get_package_dir() / PROJECT_NAME


def load_project():
    p = Project()
    p.load(project_path=PROJECT_PATH)
    return p


def save_project(p=None):
    p.save(project_path=PROJECT_PATH)


def copy_user_settings(overwrite=True):
    # FIXME: why are user settings not copied on new setups ???
    target = str(Path(os.path.expanduser("~")) / "user_settings.py")

    if Path(target).exists() and not overwrite:
        logging.info(f"User settings file exists at {target} and overwrite={overwrite}")
    else:
        # Install new user settings file
        source = user_settings.__file__
        shutil.copyfile(source, target)

        # Patch user settings with additional parameters
        with open(target, "a") as f:
            f.write(f"\nDEFAULT_PROJECT_PATH = '{str(PROJECT_PATH)}'\n")

        logging.info(f"Copied user_settings.py to {target}")


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


def write_task_file(task_name=None):
    s = (
        f'if __name__ == "__main__":\n'
        f"    from pybpod_tools.tasks.{task_name} import {task_name}\n"
    )
    return s


def create_tasks(overwrite=False):
    p = load_project()
    for task_name in list_submodules(module_tasks):
        if task_name not in [t.name for t in p.tasks] or overwrite:
            logging.info(f"Adding task: {task_name}")

            task_obj = p.create_task()
            task_obj.name = task_name
            p.save(project_path=PROJECT_PATH)
            with open(task_obj.filepath, "w") as f:
                f.write(write_task_file(task_name=task_name))


def create_users(users=None):
    p = load_project()
    for user_name in users:
        if user_name not in [u.name for u in p.users]:
            logging.info(f"Adding user: {user_name}")

            p = load_project()
            user = p.create_user()
            user.name = user_name
            save_project(p=p)


def create_boards(name_port_tuples=None, overwrite=False):
    p = load_project()
    for board_name, port in name_port_tuples:
        if board_name not in [b.name for b in p.boards] or overwrite:
            logging.info(f"Adding board: {board_name} at port {port}")

            board = p.create_board()
            board.name = board_name
            if port is not None:
                board.serial_port = port
            save_project(p=p)


def create_subjects(subjects=None, overwrite=True):
    p = load_project()

    # find additional subjects in config
    if not isinstance(subjects, list) and isinstance(subjects, str):
        subjects = [subjects]

    subjects += install_settings.SUBJECTS

    for subject_name in subjects:
        if subject_name not in [s.name for s in p.subjects] or overwrite:
            logging.info(f"Adding subject: {subject_name}")
            subj = p.create_subject()
            subj.name = subject_name
            save_project(p=p)


def update_git_repo():
    repo = git.Repo(path=get_package_dir(), search_parent_directories=True)
    print(f"Updating git repo at {repo.git_dir}")
    repo.remotes.origin.pull()

    short_sha = repo.git.rev_parse(repo.head.object.hexsha, short=True)
    print(f"Code up-to-date at {short_sha} on active branch {repo.active_branch.path}")


def run_check_install(overwrite_settings=True, overwrite_project_items=False):
    this_time = time.time()
    update_git_repo()
    copy_user_settings(overwrite=overwrite_settings)
    create_project()
    create_tasks(overwrite=overwrite_project_items)
    create_users(users=["_tests", "lbr"])
    create_boards(
        name_port_tuples=[("bpod_1", "/dev/ttyACM1")], overwrite=overwrite_project_items
    )
    create_subjects(subjects=["_test_subject"], overwrite=overwrite_project_items)

    # Adding basic experiments
    p = load_project()
    exp_name = "TEST_experiment"
    if exp_name not in [e.name for e in p.experiments] or overwrite_project_items:
        logging.info(f"Creating: {exp_name}")
        exp = p.create_experiment()
        exp.name = exp_name
        exp.task = [t for t in p.tasks if "_test__flush_water" in t.name][0]
        setup = exp.create_setup()
        setup.name = "TEST_setup"
        setup.board = p.boards[0]
        setup.detached = True
        setup += [s for s in p.subjects if "_test_subject" in s.name][0]
        setup.task = exp.task
        save_project(p=p)
        logging.info(f"Done: {exp_name} added")

    exp_name = "MAIN_experiment"
    if exp_name not in [e.name for e in p.experiments] or overwrite_project_items:
        logging.info(f"Creating: {exp_name}")
        exp = p.create_experiment()
        exp.name = exp_name
        exp.task = [t for t in p.tasks if "flush" in t.name][0]
        setup = exp.create_setup()
        setup.name = "MAIN_setup"
        setup.board = p.boards[0]
        setup.detached = True
        setup += [s for s in p.subjects if "_test_subject" in s.name][0]
        setup.task = exp.task
        save_project(p=p)
        logging.info(f"Done: {exp_name} added")

    logging.info(f"Finished all install tasks. Took {time.time()-this_time}s.")
