import contextlib
import logging
import subprocess
import sys
import time
import uuid
from datetime import UTC
from importlib.metadata import version as _get_version
from pathlib import Path
from threading import Thread
from typing import Any

import yaml
from pybpodapi.protocol import Bpod, StateMachine

from murineshiftwork.hardware.bpod import BpodFactory
from murineshiftwork.logic.hooks import (
    HookContext,
    SessionAbortError,
    collect_hooks,
    run_post_hooks,
    run_pre_hooks,
)
from murineshiftwork.logic.log import (
    add_session_log_handler,
    patch_logging_levels,
)
from murineshiftwork.logic.misc import (
    find_task_by_name,
    print_box,
    test_serial_port_is_accessible,
)
from murineshiftwork.logic.paths import build_data_paths, test_path_is_writable


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
    with Path(yaml_path).open("w") as f:
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

    bpod: Any = None
    input_kwargs: dict = {}
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


class TaskProcess:
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
    input_kwargs: dict = {}
    # Run task
    session_paths = None
    bpod: Any = None
    bpod_baudrate = 115200
    serial_is_open = False
    task_runner = None
    # Hooks
    _pre_hooks: list = []
    _post_hooks: list = []
    _hook_ctx: Any = None
    # LogAgent relay
    _relay_queue: Any = None
    _relay_proc: Any = None
    session_uuid: str = ""
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
        devices: dict | None = None,
        auto_init=True,
        auto_start=True,
        is_child_session_to=None,
        require_bpod=True,
        simulate=False,
        **kwargs,
    ):
        super().__init__()
        self.serial_port = str(serial_port_bpod) if serial_port_bpod else ""
        self.out_path = str(out_path)
        self.subject = str(subject)
        self.task_in = str(task)
        self.input_kwargs = kwargs
        self.input_kwargs["subject"] = self.subject
        self.debug = self.input_kwargs.get("debug", False)
        self.simulate = simulate
        self.session_uuid = str(uuid.uuid4())

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

        Path(self.session_paths["session_folder"]).mkdir(parents=True, exist_ok=False)
        target_file = Path(self.session_paths["session_folder"]) / ".write_test"
        if not test_path_is_writable(target_file) and not self.debug:
            raise PermissionError(f"Session files not writable at {str(target_file)}")

        patch_logging_levels()
        add_session_log_handler(self.session_paths["session_file_path"])
        logging.info(
            "Session: task=%s subject=%s setup=%s",
            self.task_name,
            self.subject,
            self.input_kwargs.get("setup", ""),
        )
        logging.info("Session folder: %s", self.session_paths.get("session_folder", ""))
        self.persist_settings()
        self._start_relay()

        if bpod is None and devices is not None:
            bpod = devices.get("bpod")

        if bpod is not None:
            logging.info("Bpod: using injected handle")
            self.bpod = bpod
            self.serial_is_open = True
        elif self.simulate:
            from murineshiftwork.hardware.bpod.sim import SimBpod

            logging.info("Bpod: simulation mode (SimBpod)")
            self.bpod = SimBpod()
            self.bpod.open()
            self.serial_is_open = True
        elif require_bpod:
            if self.serial_port:
                logging.info("Bpod: preflight check on %s", self.serial_port)
                accessible = test_serial_port_is_accessible(
                    port=self.serial_port,
                    baudrate=self.bpod_baudrate,
                    timeout=1,
                )
                if not accessible and not self.debug:
                    raise OSError(f"Serial port not accessible at {self.serial_port}")
            self.connect_bpod()

        # Build hook context and load hooks (after bpod is connected)
        _task_settings = self.input_kwargs.get("settings.task.patched", {})
        _execution_config = self.input_kwargs.get("execution_config")
        _setup_config = (
            _execution_config.setup if _execution_config is not None else None
        )
        self._hook_ctx = HookContext(
            subject=self.subject,
            task_name=self.task_name,
            task_settings=_task_settings,
            session_paths=self.session_paths,
            execution_config=_execution_config,
        )
        self._pre_hooks, self._post_hooks = collect_hooks(_setup_config, _task_settings)

        if auto_init:
            try:
                run_pre_hooks(self._pre_hooks, self._hook_ctx)
            except SessionAbortError:
                self.exit_safely()
                raise
            logging.info("Task init: %s", self.task_name)
            self.init_task()
        if auto_start:
            logging.info("Task start: %s", self.task_name)
            self.run_task()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        post_exc = None
        if self._hook_ctx is not None:
            try:
                run_post_hooks(self._post_hooks, self._hook_ctx)
            except SessionAbortError as exc:
                post_exc = exc
        self.exit_safely()
        if post_exc is not None:
            raise post_exc

    def _start_relay(self) -> None:
        from murineshiftwork.logic.machine_config import read_machine_config

        mc = read_machine_config()
        log_url = mc.get("log_url", "")
        if not log_url:
            return

        import multiprocessing
        from datetime import datetime

        from murineshiftwork.logagent.logagent import LogAgent

        bearer_token = mc.get("log_bearer_token", "")
        self._relay_queue = multiprocessing.Queue(maxsize=500)
        setup = self.input_kwargs.get("setup", "") or self.input_kwargs.get(
            "metadata", {}
        ).get("setup", "")
        session_start_payload = {
            "subject": self.subject,
            "task": self.task_name,
            "setup": setup,
            "session_uuid": self.session_uuid,
            "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "session_paths": {k: str(v) for k, v in (self.session_paths or {}).items()},
        }
        self._relay_proc = LogAgent(
            self._relay_queue,
            log_url,
            setup=setup,
            session_start_payload=session_start_payload,
            session_uuid=self.session_uuid,
            bearer_token=bearer_token,
        )
        self._relay_proc.start()
        self.input_kwargs["relay_queue"] = self._relay_queue
        logging.debug("LogAgent started → %s (setup=%r)", log_url, setup)

    def exit_safely(self):
        self.exiting = True
        if self.serial_is_open and self.bpod is not None:
            self.bpod.close_safely()
            self.serial_is_open = False
        if self._relay_queue is not None:
            with contextlib.suppress(Exception):
                self._relay_queue.put_nowait(None)
            self._relay_queue = None

    def connect_bpod(self, max_try=None, retry_delay_s=None):
        """Connect device on serial port.

        max_try and retry_delay_s are forwarded to BpodFactory; when None,
        BpodFactory uses its own defaults (connect_retries=3, retry_delay_s=2.0).
        """
        if not self.serial_is_open and not self.exiting:
            logging.debug(f"Connecting bpod on serial port: {self.serial_port}")
            kwargs: dict = dict(
                serial_port=self.serial_port,
                workspace_path=self.session_paths["session_folder"],
                session_name=self.session_paths["session_basename_behav"],
            )
            if max_try is not None:
                kwargs["connect_retries"] = max_try
            if retry_delay_s is not None:
                kwargs["retry_delay_s"] = retry_delay_s
            try:
                self.bpod = BpodFactory(**kwargs)
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
                "session_uuid": self.session_uuid,
                "task": self.task_name,
                "subject": self.subject,
                "setup": self.input_kwargs.get("setup", ""),
                "serial_port": self.serial_port,
                "out_path": self.out_path,
                "session_folder": str(self.session_paths.get("session_folder", "")),
                "session_basename": self.session_paths.get("session_basename", ""),
                "datetime": self.session_paths.get("datetime", ""),
            },
        }
        yaml_path = self.session_paths["session_file_path"] + ".msw.session.yaml"
        with Path(yaml_path).open("w") as f:
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
        import shutil

        try:
            mod = importlib.import_module(
                f"murineshiftwork.tasks.{self.task_name}.{self.task_name}"
            )
            TaskClass = getattr(mod, "Task")
        except (ImportError, AttributeError) as exc:
            raise ImportError(
                f"Cannot import 'Task' from task '{self.task_name}': {exc}"
            )

        plot_spec_src = Path(mod.__file__).parent / "plot_spec.yaml"
        if plot_spec_src.exists():
            dest = Path(self.session_paths["session_file_path"] + ".msw.plot_spec.yaml")
            shutil.copy2(plot_spec_src, dest)
            logging.debug("plot_spec copied: %s", dest.name)

        self.task_runner = TaskClass(bpod=self.bpod, **self.input_kwargs)

    def run_task(self):
        """Run the Task thread."""
        self.task_runner.start()
        time.sleep(0.1)

    def is_running(self):
        return self.task_runner.is_alive()

    def stop_task(self):
        if self.task_runner is not None and self.is_running():
            self.task_runner.continue_task = False
            self.bpod.stop_trial()
            logging.debug("Task stopped.")
