import argparse
import logging
import os
import time
from pathlib import Path

from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from PyQt5.QtCore import QThread

import murine_shift_work.settings as msws
from murine_shift_work.logic.config import read_config
from murine_shift_work.logic.misc import find_task_by_name
from murine_shift_work.logic.misc import test_port_accessible
from murine_shift_work.logic.paths import build_data_paths
from murine_shift_work.logic.paths import test_path_is_writable
from murine_shift_work.logic.pybpod_helpers import get_subject_from_pybpod_conf
from murine_shift_work.logic.run_install_tasks import get_default_basepath

user_dir = Path(os.path.expanduser("~"))
config_file_dir = str(msws.__path__[0])


def parse_task_args(is_cli_call=True, testing=False, task=None):
    parser = argparse.ArgumentParser(
        description="Input arguments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--serial-port",
        "-p",
        type=str,
        default="/dev/ttyACM0",
        help="Serial port for bpod. Unix: /dev/ttyACM{no}. Windows: COM{no}.",
    )
    parser.add_argument(
        "--basepath",
        "-f",
        type=str,
        default=str(user_dir / "data"),
        help="Basepath for task data. Default: ~/data/",
    )
    parser.add_argument(
        "--subject",
        "-s",
        type=str,
        default="_test_subject",
        help="Subject name",
    )
    parser.add_argument(
        "--task",
        "-t",
        type=str,
        default="",
        help="Task name or part name, e.g. 'optotagging' or 'opto' for task 'optotagging'",
    )
    parser.add_argument(
        "--config-file-dir",
        "-cd",
        type=str,
        default=config_file_dir,
        help="Directory that contains config files",
    )
    parser.add_argument(
        "--config-file-rcc",
        "-cr",
        type=str,
        default=str(Path(config_file_dir) / "camera.rcc.config"),
        help="Specific config file for video recordings wtih RPi Camera Colony pacakge.",
    )
    arg_dict = parser.parse_args().__dict__
    arg_dict["is_cli_call"] = is_cli_call
    arg_dict["testing"] = testing

    # Checks
    if not is_cli_call:
        arg_dict["subject"] = get_subject_from_pybpod_conf()
        arg_dict["basepath"] = get_default_basepath()

    if testing:
        arg_dict["task"] = "minimal"

    if not arg_dict["task"] and task is None and not is_cli_call:
        raise ValueError(
            "No Task to run specified. No default, has to be specified explicitly."
        )
    if not arg_dict["task"]:
        arg_dict["task"] = task

    # Prepare arguments
    arg_dict["basepath"] = os.path.expanduser(arg_dict["basepath"])
    task_name = find_task_by_name(task_name=arg_dict["task"])
    arg_dict["task_name"] = task_name
    config_file_dir_from_args = arg_dict["config_file_dir"]

    # Load settings for task and overwrite with subject-specific settings if available
    arg_dict["task.settings.default"] = {}
    arg_dict["task.settings.patched"] = {}
    arg_dict["subject.settings.all"] = {}
    arg_dict["subject.settings.this"] = {}

    # Load: task settings
    exec(f"from murine_shift_work.tasks import {task_name} as tn", globals())
    exec("task_folder = Path(tn.__file__).parent", globals())
    if "task_folder" not in locals():
        task_folder = None
    task_files = os.listdir(task_folder)
    task_settings_file = [
        Path(task_folder) / t for t in task_files if "task.settings" in t
    ]
    if len(task_settings_file) == 1:
        arg_dict["task.settings.default"] = read_config(file=task_settings_file[0])
        arg_dict["task.settings.patched"] = arg_dict["task.settings.default"]

    # Load: subject settings
    subject_settings_file = [
        Path(config_file_dir_from_args) / t
        for t in os.listdir(config_file_dir_from_args)
        if "subject.settings" in t
    ]
    if len(subject_settings_file) == 1:
        arg_dict["subject.settings.all"] = read_config(file=subject_settings_file[0])

    # Patch: default settings with subject settings
    subject_settings_this = arg_dict["subject.settings.all"].get(
        arg_dict["subject"], None
    )
    if subject_settings_this:
        task_settings_patch = subject_settings_this.get(arg_dict["task_name"], None)
        if task_settings_patch:
            arg_dict["subject.settings.this"] = task_settings_patch
            for k, v in task_settings_patch.items():
                # if k in arg_dict["task.settings.patched"]
                arg_dict["task.settings.patched"][k] = v

    # Find file of RCC settings
    if not Path(arg_dict["config_file_rcc"]).exists():
        arg_dict["config_file_rcc"] = str(Path(config_file_dir) / "camera.rcc.config")
        if not Path(arg_dict["config_file_rcc"]).exists():
            logging.debug(f"No RCC config file at: {arg_dict['config_file_rcc']}")

    return arg_dict


class TaskRunner(QThread):
    bpod = None
    input_kwargs = None
    continue_task = True

    def __init__(self, bpod=None, **kwargs):
        super(TaskRunner, self).__init__()
        self.bpod = bpod
        self.input_kwargs = kwargs
        self.prepare()

    def prepare(self):
        """Use input kwargs to e.g. start video, load task settings, make task objects, GUI, etc."""
        logging.debug("No 'TaskRunner.prepare()' implementation.")

    def run(self) -> None:
        """Run the main task logic:

        (1) Make task objects here or in `prepare()`
        (2) Run task (while loop contingent on `self.continue_task` and any task-specific conditions)
        (3) Shutdown / clean up

        trial_index = 0
        max_trials = 1500
        while self.continue_task and trial_index < max_trials:
            time.sleep(2)

        """
        raise NotImplementedError(
            "This function has to get re-implemented in child classes."
        )

    def stop(self):
        self.continue_task = False


class ExampleTask(TaskRunner):
    def run(self):
        trial_index = 0
        max_trials = 1500
        while self.continue_task and trial_index < max_trials:
            print(f"Trial {trial_index}")

            sma = StateMachine(bpod=self.bpod)
            sma.add_state(
                state_name="test_state_1",
                state_timer=20,
                state_change_conditions={Bpod.Events.Tup: "test_state_2"},
                output_actions=[],
            )
            sma.add_state(
                state_name="test_state_2",
                state_timer=1,
                state_change_conditions={Bpod.Events.Tup: "exit"},
                output_actions=[],
            )
            self.bpod.send_state_machine(sma)

            if not self.bpod.run_state_machine(sma):
                logging.warning("No data returned.")
                break

            trial_index += 1


class TaskProcess(object):
    # Input
    serial_port = None
    task_in = None
    task_name = None
    subject = None
    input_kwargs = {}
    # Run task
    session_paths = None
    bpod = None
    bpod_baudrate = 115200
    serial_is_open = False
    task_runner = None
    # Misc
    exiting = False

    def __init__(
        self,
        serial_port=None,
        basepath=None,
        subject=None,
        task=None,
        auto_init=True,
        auto_start=True,
        **kwargs,
    ):
        super(TaskProcess, self).__init__()

        self.serial_port = serial_port
        self.basepath = Path(basepath)
        self.subject = subject
        self.task_in = task
        self.input_kwargs = kwargs

        # Make vars
        self.task_name = find_task_by_name(task_name=self.task_in)
        self.session_paths = build_data_paths(
            basepath=self.basepath, subject=self.subject, task=self.task_name
        )

        # Assertions
        if not test_port_accessible(
            port=self.serial_port, baudrate=self.bpod_baudrate, timeout=1
        ):
            raise IOError(f"Serial port not accessible at {self.serial_port}")

        if not self.task_name:
            raise ValueError(
                f"Task to run '{self.task_in}' not found or not specific enough. {self.task_name}"
            )

        Path(self.session_paths["session_folder"]).mkdir(parents=True, exist_ok=False)
        target_file = Path(self.session_paths["session_folder"]) / ".write_test"
        if not test_path_is_writable(target_file):
            raise PermissionError(f"Session files not writable at {str(target_file)}")

        # Execute
        self.connect_bpod()

        if auto_init:
            self.init_task()
        if auto_start:
            self.run_task()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_safely()

    def __del__(self):
        self.exit_safely()

    def exit_safely(self):
        self.exiting = True
        if self.serial_is_open and not self.exiting:
            self.bpod.stop_trial()  # same method as in pybpod GUI. see bpod_base class.
            self.bpod.close()
            self.serial_is_open = False

    def connect_bpod(self):
        """Connect device on serial port."""
        if not self.serial_is_open and not self.exiting:
            logging.debug(f"Connecting bpod on serial port: {self.serial_port}")
            self.bpod = Bpod(
                serial_port=self.serial_port,
                workspace_path=self.session_paths["session_folder"],
                session_name=self.session_paths["session_basename_behav"],
            )
            self.bpod.open()
            self.serial_is_open = True

    def init_task(self):
        """Import specific Task and make self.task_runner Thread."""
        try:
            exec(
                f"from murine_shift_work.tasks.{self.task_name}.{self.task_name} import Task as ThisTask",
                globals(),
            )
            exec("self.task_runner = ThisTask(bpod=self.bpod, **self.input_kwargs)")
        except ImportError:
            raise ImportError(f"Cannot import 'Task' from task '{self.task_name}'")

    def run_task(self):
        """Run the Task thread."""
        self.task_runner.start()
        time.sleep(0.1)

    def is_running(self):
        return self.task_runner.isRunning()

    def stop_task(self):
        if self.task_runner is not None:
            if self.is_running():
                self.task_runner.continue_task = False
                self.bpod.stop_trial()
                logging.debug("Task stopped.")


def run_msw_cli(testing=False):
    args_dict = parse_task_args(is_cli_call=True, testing=testing)

    task_name = args_dict["task_name"]
    exec(
        f"from murine_shift_work.tasks.{task_name}.{task_name} import run_task",
        globals(),
    )
    exec("run_task(**args_dict)")

    logging.debug("EXITING CLI.")


if __name__ == "__main__":
    print("main")
