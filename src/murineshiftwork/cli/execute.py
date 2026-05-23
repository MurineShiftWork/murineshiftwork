import logging
import sys
from pathlib import Path

import yaml

from murineshiftwork.logic.machine_config import (
    get_machine_config_path,
    resolve_config_dir,
    write_machine_config,
)
from murineshiftwork.logic.misc import print_box


def _apply_stage_position(args_dict: dict) -> None:
    """Move stage to the named position from task settings before task starts."""
    patched = args_dict.get("settings.task.patched", {})
    position_name = patched.get("stage_position")
    serial_port_stage = args_dict.get("serial_port_stage", "")
    if not position_name or not serial_port_stage:
        return

    calib_path = Path(patched.get("calibration_file_stage", "")).expanduser()
    if not calib_path.exists():
        logging.warning(
            f"stage_position '{position_name}' set but calibration file not found: {calib_path}"
        )
        return

    from one_axis_stage.controller import StageController

    with open(calib_path) as f:
        config = yaml.safe_load(f)
    config["connection"]["serial_port"] = serial_port_stage
    known = config.get("known_positions", {})
    if position_name not in known:
        logging.warning(
            f"stage_position '{position_name}' not in known_positions of {calib_path.name}"
        )
        return

    ctrl = StageController.from_config(config)
    target = known[position_name]
    for axis_name, axis_cfg in target.items():
        axis = ctrl.axes.get(axis_name)
        if axis is not None and hasattr(axis, "move_to"):
            axis.move_to(**axis_cfg)
    ctrl.disconnect()
    logging.info(f"Stage moved to position '{position_name}'")


def run_task(**args_dict):
    """
    msw run -s subject -t task
    msw run -s subject -t task -p serial_port
    """
    import importlib

    from murineshiftwork.logic.log import suppress_third_party_console_handlers

    suppress_third_party_console_handlers()  # catch handlers added at import time
    _apply_stage_position(args_dict)
    task_name = args_dict["task"]
    mod = importlib.import_module(f"murineshiftwork.tasks.{task_name}.{task_name}")

    serial_port = args_dict.get("serial_port_bpod", "")
    if serial_port and not args_dict.get("simulate") and not args_dict.get("bpod"):
        from murineshiftwork.hardware.bpod.device import BpodDevice
        from murineshiftwork.hardware.manager import HardwareManager

        with HardwareManager([BpodDevice(serial_port=serial_port)]) as devices:
            args_dict["bpod"] = devices["bpod"]
            mod.run_task(**args_dict)
    else:
        mod.run_task(**args_dict)

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

    extra = {}
    data_dir_arg = args_dict.get("data_dir", "")
    if data_dir_arg:
        data_dir = Path(data_dir_arg).expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        extra["data_dir"] = str(data_dir)

    write_machine_config(config_dir, **extra)

    data_line = (
        f"Data dir:   {extra.get('data_dir', '(not set — defaults to ~/data)')}\n"
        if extra.get("data_dir")
        else ""
    )
    print_box(
        f"Initialised MSW on this machine.\n"
        f"Config dir: {config_dir}\n"
        f"{data_line}"
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
        if not setup_name or not setup_name.strip():
            print(
                "Error: setup name is required. Usage: msw setup create <setup_name>",
                file=sys.stderr,
            )
            sys.exit(1)
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
                "bpod": {
                    "type": "bpod",
                    "port_by_path": "FILL_IN_PORT_BY_PATH",
                },
            },
            "calibrations": {"bpod_valve": {}},
        }
        with open(path, "w") as f:
            yaml.dump(
                skeleton,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        print_box(
            f"Created setup config skeleton: {path}\nEdit the file to fill in device port_by_path values."
        )

    elif subcommand == "list":
        if not setups_dir.exists():
            print_box(f"No setups dir at {setups_dir}")
            return
        filt = args_dict.get("filter", "").lower()
        setups = sorted(p.stem for p in setups_dir.glob("*.yaml"))
        if filt:
            setups = [s for s in setups if filt in s.lower()]
        print_box(
            f"Available setups in {setups_dir}:\n"
            + "\n".join(f"  - {s}" for s in setups)
        )

    elif subcommand == "rename":
        setup_name = args_dict["setup_name"]
        new_name = args_dict.get("new_name", "")
        if not setup_name:
            print(
                "Error: setup name is required. Usage: msw setup rename <name> --new-name <new>",
                file=sys.stderr,
            )
            sys.exit(1)
        if not new_name:
            print_box("--new-name is required for 'rename'.")
            return
        old_path = setups_dir / f"{setup_name}.yaml"
        new_path = setups_dir / f"{new_name}.yaml"
        if not old_path.exists():
            print_box(f"Setup '{setup_name}' not found at {old_path}.")
            return
        if new_path.exists() and not args_dict.get("force", False):
            print_box(
                f"Setup '{new_name}' already exists at {new_path}. Use --force to overwrite."
            )
            return
        old_path.rename(new_path)
        with open(new_path) as f:
            raw = yaml.safe_load(f) or {}
        raw["name"] = new_name
        with open(new_path, "w") as f:
            yaml.dump(
                raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )
        print_box(f"Renamed setup '{setup_name}' → '{new_name}'.")

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
        if not subject_name or not subject_name.strip():
            print(
                "Error: subject name is required. Usage: msw subject add -s <name>",
                file=__import__("sys").stderr,
            )
            __import__("sys").exit(1)
        path = subjects_dir / f"{subject_name}.yaml"
        if path.exists() and not args_dict.get("force", False):
            print_box(f"Subject '{subject_name}' already exists at {path}.")
            return

        data = {
            "name": subject_name,
            "registered": __import__("datetime")
            .datetime.now()
            .isoformat(timespec="seconds"),
            "project": args_dict.get("project", ""),
            "experiment": args_dict.get("experiment", ""),
            "comment": args_dict.get("comment", ""),
            "aliases": [],
            "task_overrides": {},
        }
        with open(path, "w") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
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

    elif subcommand == "rename":
        subject_name = args_dict["subject"]
        new_name = args_dict.get("new_name", "")
        if not new_name:
            print_box("--new-name is required for 'rename'.")
            return
        old_path = subjects_dir / f"{subject_name}.yaml"
        new_path = subjects_dir / f"{new_name}.yaml"
        if not old_path.exists():
            print_box(f"Subject '{subject_name}' not found at {old_path}.")
            return
        if new_path.exists() and not args_dict.get("force", False):
            print_box(
                f"Subject '{new_name}' already exists at {new_path}. Use --force to overwrite."
            )
            return
        old_path.rename(new_path)
        with open(new_path) as f:
            raw = yaml.safe_load(f) or {}
        raw["name"] = new_name
        with open(new_path, "w") as f:
            yaml.dump(
                raw,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        print_box(f"Renamed subject '{subject_name}' → '{new_name}'.")

    elif subcommand == "remove":
        subject_name = args_dict["subject"]
        path = subjects_dir / f"{subject_name}.yaml"
        if path.exists():
            path.unlink()
            print_box(f"Removed subject '{subject_name}' (deleted {path}).")
        else:
            print_box(f"Subject '{subject_name}' not found at {path}.")

    else:
        raise ValueError(f"Unknown subject subcommand: {subcommand!r}")


# ---------------------------------------------------------------------------
# murineshiftwork action


def _parse_action_param(v: str):
    """Coerce a KEY=VALUE string value to int, float, or str."""
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def run_action(**args_dict):
    """msw action --setup <name> <device> <action> [key=value ...]

    Phase 1: opens a fresh Bpod connection, executes the action, disconnects.
    The connection is exclusive — do not run while a task session is active.
    """
    from murineshiftwork.hardware.bpod.actions import BpodActionDriver
    from murineshiftwork.hardware.bpod.factory import BpodFactory
    from murineshiftwork.logic.config.io import load_setup_config
    from murineshiftwork.logic.config.models import ActionRequest
    from murineshiftwork.logic.machine_config import resolve_config_dir

    setup_name = args_dict["setup"]
    device_key = args_dict["device"]
    action = args_dict["action"]
    params_raw = args_dict.get("params") or []

    params = {}
    for kv in params_raw:
        k, _, v = kv.partition("=")
        params[k.strip()] = _parse_action_param(v.strip())

    request = ActionRequest(
        setup=setup_name,
        device=device_key,
        action=action,
        params=params,
    )

    config_dir = resolve_config_dir(args_dict.get("config_dir", ""))
    setup_cfg = load_setup_config(config_dir, setup_name)
    if setup_cfg is None:
        raise ValueError(f"Setup '{setup_name}' not found in {config_dir}/setups/")

    device = setup_cfg.devices.get(device_key)
    if device is None:
        raise KeyError(
            f"Device '{device_key}' not in setup '{setup_name}'. "
            f"Available devices: {list(setup_cfg.devices)}"
        )

    serial_port = args_dict.get("serial_port_bpod", "/dev/ttyACM0")

    if device.type == "bpod":
        with BpodFactory(serial_port=serial_port) as bpod:
            bpod.open()
            driver = BpodActionDriver(bpod)
            driver.dispatch(request)
    else:
        raise ValueError(
            f"No action driver registered for device type '{device.type}'. "
            f"Supported: 'bpod'"
        )


# ---------------------------------------------------------------------------
# murineshiftwork calibration


def run_agent(**args_dict):
    """msw agent start --setup <name> [--port 8765]

    Starts a long-lived FastAPI agent that owns the Bpod connection across
    sessions.  The CLI (``msw run``) remains the primary session entry point;
    the agent adds hardware persistence and a WebSocket event bus for read-only
    UI observers.
    """
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "The 'agent' extra is not installed.\n"
            "Run: pip install 'murineshiftwork[agent]'"
        ) from exc

    from murineshiftwork.agent.app import create_app
    from murineshiftwork.logic.config.io import load_setup_config
    from murineshiftwork.logic.machine_config import resolve_config_dir

    subcommand = args_dict.get("subcommand")
    if subcommand != "start":
        raise ValueError(f"Unknown agent subcommand: {subcommand!r}")

    setup_name = args_dict["setup"]
    port = args_dict.get("agent_port", 8765)
    host = args_dict.get("agent_host", "0.0.0.0")

    config_dir = resolve_config_dir(args_dict.get("config_dir", ""))
    setup_cfg = load_setup_config(config_dir, setup_name)
    if setup_cfg is None:
        raise ValueError(f"Setup '{setup_name}' not found in {config_dir}/setups/")

    bpod_device = setup_cfg.devices.get("bpod")
    serial_port = args_dict.get("serial_port_bpod") or (
        bpod_device.port
        if bpod_device and hasattr(bpod_device, "port")
        else "/dev/ttyACM0"
    )

    app = create_app(setup=setup_name, serial_port=serial_port, config_dir=config_dir)
    uvicorn.run(app, host=host, port=port)


def run_calibration(**args_dict):
    """Plot and save calibration charts as PDF."""
    from murineshiftwork.logic.calibration import save_calibration_pdfs
    from murineshiftwork.logic.log import setup_logging
    from murineshiftwork.logic.machine_config import resolve_config_dir

    setup_logging(level="INFO")

    config_dir = resolve_config_dir(args_dict.get("config_dir", ""))
    output_dir = args_dict.get("output_dir", ".")
    setup_name = args_dict.get("setup") or None

    saved = save_calibration_pdfs(
        config_dir=config_dir,
        setup_name=setup_name,
        output_dir=output_dir,
    )
    for path in saved:
        print(f"Saved: {path}")
    if not saved:
        print(
            "No calibration PDFs saved — check setup YAMLs contain bpod_valve calibration data."
        )
