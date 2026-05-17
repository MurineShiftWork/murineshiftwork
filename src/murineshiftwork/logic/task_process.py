import logging
import subprocess
import sys
import time
from importlib.metadata import version as _get_version
from pathlib import Path
from threading import Thread

import numpy as np
import yaml
from murineshiftwork.hardware.bpod import BpodFactory
from murineshiftwork.logic.log import add_session_log_handler
from murineshiftwork.logic.log import patch_logging_levels
from murineshiftwork.logic.misc import find_task_by_name
from murineshiftwork.logic.misc import print_box
from murineshiftwork.logic.misc import test_serial_port_is_accessible
from murineshiftwork.logic.paths import build_data_paths
from murineshiftwork.logic.paths import test_path_is_writable
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine


def _get_git_commit() -> str:
    """Return the short git commit hash of the current HEAD, or '' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def update_session_yaml(session_file_path, **sections):
    """Add or update top-level sections in .msw.session.yaml.

    Creates the file with msw_format_version: 2 if it does not exist yet.
    Typical callers: task_objects writing task_settings or stage after init.
    """
    yaml_path = str(session_file_path) + ".msw.session.yaml"
    p = Path(yaml_path)
    if p.exists():
        data = yaml.safe_load(p.read_text()) or {}
    else:
        data = {"msw_format_version": 2}
    data.update(sections)
    with open(yaml_path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


class TaskRunner(Thread):
    """Base class for task threads.

    Subclass and override ``run()``.  Check ``self.continue_task`` in the run
    loop so ``stop()`` can interrupt gracefully.  No Qt dependency — GUI layers
    can wrap this in a QThread adapter if needed.
    """

    bpod = None
    input_kwargs = None
    continue_task = True

    def __init__(self, bpod=None, **kwargs):
        super().__init__(daemon=True)
        self.bpod = bpod
        self.input_kwargs = kwargs
        self.prepare()

    def prepare(self):
        """Override for setup work before the task starts (load settings, open video, etc.)."""
        logging.debug("No 'TaskRunner.prepare()' implementation.")

    def run(self) -> None:
        """Override with task loop logic.

        trial_index = 0
        max_trials = 1500
        while self.continue_task and trial_index < max_trials:
            ...
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
    """Manages one session: paths, bpod connection, task thread lifecycle.

    Bpod injection: pass a pre-opened ``RobustBpodSession`` via ``bpod=`` to let
    the caller (controller/hardware manager) own the hardware connection.  When
    ``bpod`` is None (default), TaskProcess opens the connection itself using
    ``serial_port_bpod``.
    """

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
    debug = False

    def __init__(
        self,
        serial_port_bpod=None,
        out_path=None,
        subject=None,
        task=None,
        bpod=None,
        auto_init=True,
        auto_start=True,
        is_child_session_to=None,
        require_bpod=True,
        **kwargs,
    ):
        super(TaskProcess, self).__init__()
        self.serial_port = str(serial_port_bpod) if serial_port_bpod else ""
        self.out_path = str(out_path)
        self.subject = str(subject)
        self.task_in = str(task)
        self.input_kwargs = kwargs
        self.debug = self.input_kwargs.get("debug", False)

        self.task_name = find_task_by_name(task_name=self.task_in)
        self.session_paths = build_data_paths(
            basepath=Path(self.out_path),
            subject=self.subject,
            task=self.task_name,
            is_child_session_to=is_child_session_to,
        )
        self.input_kwargs["task_name"] = self.task_name
        self.input_kwargs["session_paths"] = self.session_paths

        if not self.task_name and not self.debug:
            raise ValueError(
                f"Task to run '{self.task_in}' not found or not specific enough."
            )

        Path(self.session_paths["session_folder"]).mkdir(
            parents=True, exist_ok=False
        )
        target_file = (
            Path(self.session_paths["session_folder"]) / ".write_test"
        )
        if not test_path_is_writable(target_file) and not self.debug:
            raise PermissionError(
                f"Session files not writable at {str(target_file)}"
            )

        patch_logging_levels()
        add_session_log_handler(self.session_paths["session_file_path"])
        self.persist_settings()

        if bpod is not None:
            # Injected: controller owns the hardware connection
            self.bpod = bpod
            self.serial_is_open = True
            logging.debug("TaskProcess: using injected Bpod handle")
        elif require_bpod:
            # Self-managed: open connection from serial_port_bpod arg
            if self.serial_port:
                accessible = test_serial_port_is_accessible(
                    port=self.serial_port,
                    baudrate=self.bpod_baudrate,
                    timeout=1,
                )
                if not accessible and not self.debug:
                    raise IOError(
                        f"Serial port not accessible at {self.serial_port}"
                    )
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
        if self.serial_is_open and self.bpod is not None:
            self.bpod.close_safely()
            self.serial_is_open = False

    def connect_bpod(self, max_try=2):
        """Connect device on serial port."""
        if not self.serial_is_open and not self.exiting:
            logging.debug(
                f"Connecting bpod on serial port: {self.serial_port}"
            )
            try:
                self.bpod = BpodFactory(
                    serial_port=self.serial_port,
                    workspace_path=self.session_paths["session_folder"],
                    session_name=self.session_paths["session_basename_behav"],
                    connect_retries=max_try,
                )
                self.bpod.open()
                self.serial_is_open = True
            except RuntimeError as exc:
                print_box(f"\n{exc}\n")
                sys.exit(1)

    def persist_settings(self):
        data = {
            "msw_format_version": 2,
            "process": {
                "msw_version": _get_version("murineshiftwork"),
                "git_commit": _get_git_commit(),
                "task": self.task_name,
                "subject": self.subject,
                "setup": self.input_kwargs.get("setup", ""),
                "serial_port": self.serial_port,
                "out_path": self.out_path,
                "session_folder": str(
                    self.session_paths.get("session_folder", "")
                ),
                "session_basename": self.session_paths.get(
                    "session_basename", ""
                ),
                "datetime": self.session_paths.get("datetime", ""),
            },
        }
        yaml_path = (
            self.session_paths["session_file_path"] + ".msw.session.yaml"
        )
        with open(yaml_path, "w") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def init_task(self):
        """Import specific Task and make self.task_runner Thread."""
        import importlib

        try:
            mod = importlib.import_module(
                f"murineshiftwork.tasks.{self.task_name}.{self.task_name}"
            )
            TaskClass = getattr(mod, "Task")
        except (ImportError, AttributeError) as exc:
            raise ImportError(
                f"Cannot import 'Task' from task '{self.task_name}': {exc}"
            )
        self.task_runner = TaskClass(bpod=self.bpod, **self.input_kwargs)

    def run_task(self):
        """Run the Task thread."""
        self.task_runner.start()
        time.sleep(0.1)

    def is_running(self):
        return self.task_runner.is_alive()

    def stop_task(self):
        if self.task_runner is not None:
            if self.is_running():
                self.task_runner.continue_task = False
                self.bpod.stop_trial()
                logging.debug("Task stopped.")
