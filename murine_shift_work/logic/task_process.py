import json
import logging
import sys
import time
from pathlib import Path

from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine
from PyQt5.QtCore import QThread

from murine_shift_work.logic.misc import find_task_by_name
from murine_shift_work.logic.misc import print_box
from murine_shift_work.logic.misc import test_port_accessible
from murine_shift_work.logic.paths import build_data_paths
from murine_shift_work.logic.paths import test_path_is_writable
from murine_shift_work.logic.pybpod_helpers import patch_logging_levels


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
        serial_port_bpod=None,
        out_path=None,
        subject=None,
        task=None,
        auto_init=True,
        auto_start=True,
        **kwargs,
    ):
        super(TaskProcess, self).__init__()

        self.serial_port = str(serial_port_bpod)
        self.out_path = str(out_path)
        self.subject = str(subject)
        self.task_in = str(task)
        self.input_kwargs = kwargs

        # Make vars
        self.task_name = find_task_by_name(task_name=self.task_in)
        self.session_paths = build_data_paths(
            basepath=self.out_path, subject=self.subject, task=self.task_name
        )
        self.input_kwargs["task_name"] = self.task_name
        self.input_kwargs["session_paths"] = self.session_paths

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

        # Remove logging output for pybpod components
        patch_logging_levels()

        # Execute
        self.connect_bpod()
        self.persist_settings()

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
            try:
                self.bpod = Bpod(
                    serial_port=self.serial_port,
                    workspace_path=self.session_paths["session_folder"],
                    session_name=self.session_paths["session_basename_behav"],
                )
                self.bpod.open()
            except UnicodeDecodeError:
                print_box(
                    "\nCould not connect to Bpod due to 'UnicodeDecodeError'. "
                    "Happens randomly. Just run same code again.\n"
                )
                sys.exit(1)
            self.serial_is_open = True

    def persist_settings(self):
        settings = vars(self)
        with open(
            self.session_paths["session_file_path"] + ".msw.settings.process.json", "w"
        ) as f:
            txt = json.dumps(
                settings,
                skipkeys=True,
                sort_keys=True,
                indent=4,
                default=lambda x: f"<NoJSON:{type(x)}>",
            )
            f.write(txt)

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
