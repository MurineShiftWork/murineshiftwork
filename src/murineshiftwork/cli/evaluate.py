import logging
from pathlib import Path

import yaml

from murineshiftwork.cli.defaults import (
    DEFAULT_CALIBRATION_FILE_LIQUID,
    DEFAULT_CALIBRATION_FILE_SOUND,
    DEFAULT_CALIBRATION_FILE_STAGE,
    available_tasks,
    default_config_dir,
    default_out_path,
)
from murineshiftwork.cli.preflight import preflight_hardware_check
from murineshiftwork.cli.tasks import (
    find_task_by_name,
    list_available_tasks,
    load_task_module,
)
from murineshiftwork.logic.config import (
    ExecutionConfig,
    deep_merge,
    load_setup_config,
    load_subject_config,
    read_config,
    read_task_modes,
    save_subject_task_overrides,
    validate_config_file_path,
)
from murineshiftwork.logic.log import setup_logging
from murineshiftwork.logic.machine_config import resolve_config_dir, resolve_data_dir
from murineshiftwork.logic.paths import get_host_ip, get_host_name
from murineshiftwork.logic.task_settings import build_task_settings

# Re-export for anything that imported these from here before the split
__all__ = [
    "evaluate_args",
    "get_task_dir",
    "available_tasks",
    "default_config_dir",
    "default_out_path",
]


def get_task_dir(task=None):
    try:
        mod = load_task_module(task)
        return str(Path(mod.__file__).parent)
    except (ImportError, AttributeError):
        return ""


def _evaluate_metadata(args_dict):
    metadata_dict = {}
    # Key=value pairs from --meta
    metadata_list = args_dict.get("metadata_list", None)
    if metadata_list:
        kv_list = [v.strip().strip("'\"") for v in metadata_list if "=" in v]
        metadata_dict.update(dict(s.split("=", 1) for s in kv_list))
    # Named convenience args override --meta
    if args_dict.get("setup"):
        metadata_dict["setup"] = args_dict["setup"]
    if args_dict.get("experimenter"):
        metadata_dict["experimenter"] = args_dict["experimenter"]
    args_dict["metadata"] = metadata_dict
    return args_dict


def _evaluate_log_level(args_dict=None):
    if args_dict["debug"]:
        args_dict["log_level"] = "DEBUG"
    try:
        d_int = int(args_dict["log_level"])
        args_dict["log_int"] = d_int
        args_dict["log_level"] = logging.getLevelName(d_int)
    except ValueError:
        pass
    return args_dict


def _evaluate_task(args_dict=None):
    if args_dict["task"]:
        requested = args_dict["task"]
        args_dict["task"] = find_task_by_name(task_name=requested)
        if args_dict["task"] is None:
            raise ValueError(
                f"Unknown task '{requested}'. Available tasks:\n"
                + "\n".join(f"  {t}" for t in sorted(list_available_tasks()))
            )
        args_dict["task_dir"] = get_task_dir(task=args_dict["task"])
    else:
        raise ValueError(
            "Task name is required. Pass -t <task_name> to the run command."
        )
    return args_dict


def _evaluate_and_load_configs(args_dict=None):
    # Apply priority chain: CLI arg > env var > machine config > defaults
    config_dir = resolve_config_dir(cli_override=args_dict.get("config_dir", ""))
    args_dict["config_dir"] = config_dir
    if not Path(config_dir).exists():
        args_dict["config_dir"] = ""

    args_dict["out_path"] = resolve_data_dir(cli_override=args_dict.get("out_path", ""))

    args_dict["config_file_subjects"] = validate_config_file_path(
        config_file=args_dict.get("config_file_subjects", ""),
        default_dir=args_dict["config_dir"],
    )
    args_dict["config_file_task"] = validate_config_file_path(
        config_file=args_dict.get("config_file_task", "task.yaml"),
        default_dir=args_dict.get("task_dir", ""),
    )
    args_dict["config_file_camera"] = validate_config_file_path(
        config_file=args_dict.get("config_file_camera", ""),
        default_dir=args_dict["config_dir"],
    )
    if not args_dict["task"].startswith("_calibration"):
        args_dict["calibration_file_liquid"] = validate_config_file_path(
            config_file=args_dict.get(
                "calibration_file_liquid", DEFAULT_CALIBRATION_FILE_LIQUID
            ),
            default_dir=args_dict["config_dir"],
        )
        args_dict["calibration_file_sound"] = validate_config_file_path(
            config_file=args_dict.get(
                "calibration_file_sound", DEFAULT_CALIBRATION_FILE_SOUND
            ),
            default_dir=args_dict["config_dir"],
        )

    settings_task_default = (
        read_config(file=args_dict["config_file_task"])
        if args_dict["config_file_task"]
        else {}
    )

    # Config-dir overlay: deep-merge user edits on top of bundled defaults
    _overlay_path = (
        Path(args_dict["config_dir"]) / "tasks" / args_dict["task"] / "task.yaml"
        if args_dict.get("config_dir") and args_dict.get("task")
        else None
    )
    if _overlay_path and _overlay_path.exists():
        overlay_defaults = read_config(file=str(_overlay_path))
        settings_task_default = deep_merge(settings_task_default, overlay_defaults)
        args_dict["config_file_task_overlay"] = str(_overlay_path)
        logging.debug(f"Task config overlay applied from {_overlay_path}")
    else:
        args_dict["config_file_task_overlay"] = ""

    calibration_file_stage = args_dict.get(
        "calibration_file_stage", DEFAULT_CALIBRATION_FILE_STAGE
    )
    args_dict["calibration_file_stage"] = (
        Path(calibration_file_stage).expanduser().as_posix()
    )
    if Path(args_dict["calibration_file_stage"]).exists():
        with Path(args_dict["calibration_file_stage"]).open() as _f:
            args_dict["settings.stage"] = yaml.full_load(_f)
    else:
        args_dict["settings.stage"] = {}

    args_dict["settings.task.default"] = settings_task_default

    args_dict["setup_config"] = load_setup_config(
        config_dir=args_dict["config_dir"],
        setup_name=args_dict.get("setup", ""),
    )
    args_dict["subject_config"] = load_subject_config(
        config_dir=args_dict["config_dir"],
        subject_name=args_dict.get("subject", ""),
    )

    return args_dict


def _stage_device_to_controller_config(device) -> dict:
    """Convert a StageTowerDevice to the dict format StageController.from_config() expects."""
    return {
        "connection": {
            "baudrate": device.baudrate,
            "timeout": device.timeout,
        },
        "axes": {
            name: {
                "id": ax.id,
                "position_min": ax.position_min,
                "position_max": ax.position_max,
                "velocity_max": ax.velocity_max,
                "operating_mode": ax.operating_mode,
            }
            for name, ax in device.axes.items()
        },
        "known_positions": device.known_positions,
    }


def _extra_injections_from_args(args_dict: dict) -> dict:
    """Collect fallback-injection keys from args_dict for build_task_settings."""
    injections: dict = {}
    for key in (
        "calibration_file_liquid",
        "calibration_file_sound",
        "calibration_file_stage",
        "serial_port_stage",
        "serial_port_pulsepal",
        "serial_port_scale",
        "scale_type",
        "scale_baudrate",
        "scale_protocol",
        "settings.stage",
    ):
        if key in args_dict:
            injections[key] = args_dict[key]
    if args_dict.get("config_dir"):
        injections["config_dir"] = args_dict["config_dir"]
    return injections


def _inject_valve_calibration(setup_config, patched) -> None:
    """Inject valve_s_for_ul into patched task settings with three-tier fallback.

    Tier 1 — setup has calibration for the requested port: use it, warn if stale.
    Tier 2 — setup bpod_valve dict is entirely empty: use hardcoded fallback,
              print a loud warning; intended for debug runs only.
    Tier 3 — setup has some calibration but the requested port is missing:
              hard fail — partial config is a misconfiguration, not an absence.
    """
    from datetime import datetime, timedelta

    from murineshiftwork.logic.config._defaults import _FALLBACK_VALVE_CALIBRATION

    cal = setup_config.calibrations.bpod_valve

    if not cal:
        logging.warning(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            "NO VALVE CALIBRATION in setup '%s'.\n"
            "Using built-in fallback (generic approximate values).\n"
            "DO NOT USE THIS DATA FOR EXPERIMENTS — calibrate first.\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
            setup_config.name,
        )
        fallback = _FALLBACK_VALVE_CALIBRATION
        patched["valve_s_for_ul"] = lambda vol, port=None: fallback.s_for_ul(vol)
        return

    # Build a lookup using the SetupConfig method but also check staleness per port.
    stale_threshold = datetime.now() - timedelta(
        days=setup_config.calibrations.stale_days
    )
    for port, vc in cal.items():
        if vc.updated:
            try:
                updated_dt = datetime.fromisoformat(vc.updated)
                if updated_dt < stale_threshold:
                    age_days = (datetime.now() - updated_dt).days
                    logging.warning(
                        "Valve %s calibration on setup '%s' is %d days old "
                        "(last updated %s) — recalibrate before data collection.",
                        port,
                        setup_config.name,
                        age_days,
                        vc.updated[:10],
                    )
            except ValueError:
                pass

    available_ports = sorted(cal.keys())

    def _valve_s_for_ul_checked(port, volume_ul, _cal=cal, _sc=setup_config):
        if str(port) not in _cal:
            raise ValueError(
                f"Valve port {port!r} has no calibration in setup '{_sc.name}'. "
                f"Calibrated ports: {available_ports}. "
                "Calibrate this valve before running a session with reward delivery."
            )
        return _sc.valve_s_for_ul(port, volume_ul)

    patched["valve_s_for_ul"] = _valve_s_for_ul_checked
    logging.debug("Injected valve_s_for_ul from SetupConfig into task settings")


def _resolve_setup_config_ports(args_dict, setup_config, patched):
    """Apply port and camera overrides from SetupConfig into args_dict and patched."""
    if setup_config and "bpod" in setup_config.devices:
        try:
            resolved = setup_config.device_port("bpod")
            args_dict["serial_port_bpod"] = resolved
            logging.debug(f"Resolved bpod port from SetupConfig: {resolved}")
        except ValueError as exc:
            logging.warning(
                f"SetupConfig bpod port resolution failed ({exc}); "
                f"using CLI value {args_dict['serial_port_bpod']!r}"
            )

    if setup_config and "stage" in setup_config.devices:
        stage_dev = setup_config.devices["stage"]
        try:
            resolved_stage = setup_config.device_port("stage")
            args_dict["serial_port_stage"] = resolved_stage
            patched["serial_port_stage"] = resolved_stage
            logging.debug(f"Resolved stage port from SetupConfig: {resolved_stage}")
        except ValueError as exc:
            logging.warning(f"SetupConfig stage port resolution failed ({exc})")
        # Always prefer setup config axes over old calibration files
        args_dict["settings.stage"] = _stage_device_to_controller_config(stage_dev)
        patched["settings.stage"] = args_dict["settings.stage"]
        logging.debug("Built settings.stage from SetupConfig stage device")

    if setup_config and "scale" in setup_config.devices:
        scale_dev = setup_config.devices["scale"]
        try:
            resolved_scale = setup_config.device_port("scale")
            args_dict["serial_port_scale"] = resolved_scale
            patched["serial_port_scale"] = resolved_scale
            logging.debug(f"Resolved scale port from SetupConfig: {resolved_scale}")
        except ValueError as exc:
            logging.warning(
                f"SetupConfig scale port resolution failed ({exc}); "
                f"using CLI value {args_dict['serial_port_scale']!r}"
            )
        scale_type = getattr(scale_dev, "scale_type", "hx711")
        scale_baudrate = getattr(scale_dev, "baudrate", 4800)
        scale_protocol = getattr(scale_dev, "scale_protocol", None)
        args_dict["scale_type"] = scale_type
        args_dict["scale_baudrate"] = scale_baudrate
        args_dict["scale_protocol"] = scale_protocol
        patched["scale_type"] = scale_type

    if setup_config and "pulsepal" in setup_config.devices:
        try:
            resolved_pp = setup_config.device_port("pulsepal")
            args_dict["serial_port_pulsepal"] = resolved_pp
            patched["serial_port_pulsepal"] = resolved_pp
            logging.debug(f"Resolved pulsepal port from SetupConfig: {resolved_pp}")
        except ValueError as exc:
            logging.warning(
                f"SetupConfig pulsepal port resolution failed ({exc}); skipping pulsepal"
            )
            args_dict["serial_port_pulsepal"] = ""
            patched.pop("serial_port_pulsepal", None)
    elif setup_config:
        args_dict["serial_port_pulsepal"] = ""
        patched.pop("serial_port_pulsepal", None)

    if setup_config and setup_config.cameras:
        cam_path = setup_config.cameras.config
        if cam_path and (
            not args_dict.get("config_file_camera")
            or not Path(args_dict.get("config_file_camera", "")).exists()
        ):
            args_dict["config_file_camera"] = cam_path
            logging.debug(f"Resolved camera config from SetupConfig: {cam_path}")
        args_dict["cameras_config"] = setup_config.cameras

    if setup_config:
        _inject_valve_calibration(setup_config, patched)


def _parse_host_flag(value: str) -> tuple[str, str]:
    """Parse ``TYPE`` or ``TYPE:URL`` from --host flag value."""
    parts = value.strip().split(":", 1)
    return parts[0].strip().lower(), (parts[1].strip() if len(parts) > 1 else "")


def _resolve_host_session(args_dict: dict) -> None:
    """Attach to a host acquisition session and populate linked_to.

    Reads ``--host TYPE[:URL]`` from args_dict.  URL is optional: if omitted,
    the backend-specific address is read from setup YAML or machine config.

    No-op when ``--host`` is absent.  Does not overwrite ``--link-to`` if already set.
    """
    host_flag = args_dict.get("host_flag", "")
    if not host_flag:
        return

    session_type, url_override = _parse_host_flag(host_flag)

    # URL resolution — openephys reads from setup YAML or machine config when not in flag
    url = url_override
    if not url and session_type in ("openephys", "open_ephys"):
        setup_config = args_dict.get("setup_config")
        if setup_config is not None:
            url = getattr(setup_config, "open_ephys_url", "") or ""
        if not url:
            from murineshiftwork.logic.machine_config import read_open_ephys_url

            url = read_open_ephys_url()
        if not url:
            logging.warning(
                "--host openephys: no URL — pass as openephys:HOST or set "
                "open_ephys_url in the setup YAML"
            )
            return

    from murineshiftwork.hardware.host_session import make_host_session

    try:
        client = make_host_session(session_type, **{"url": url} if url else {})
    except (ValueError, TypeError) as exc:
        logging.warning("--host: %s", exc)
        return

    info = client.attach()

    if info is None:
        reason = getattr(client, "fail_reason", "") or "unknown reason"
        if not args_dict.get("force_standalone"):
            raise RuntimeError(
                f"\n\n  --host {session_type} @ {url} could not attach:\n"
                f"  {reason}\n\n"
                f"  Session paths cannot be determined — aborting to avoid saving\n"
                f"  data to the wrong location.\n\n"
                f"  Options:\n"
                f"    1. Fix the issue (run oe-remote record first, check URL)\n"
                f"    2. Use --link-to ACQUISITION_NAME to set the path manually\n"
                f"    3. Pass --force-standalone to intentionally run without a host\n"
            )
        logging.warning(
            "--force-standalone: host session (%s @ %s) unavailable (%s) — "
            "saving to standalone path",
            session_type,
            url,
            reason,
        )
        return

    if args_dict.get("linked_to"):
        logging.debug(
            "linked_to already set to %r — --host result discarded",
            args_dict["linked_to"],
        )
        return

    args_dict["linked_to"] = info.session_name
    args_dict["host_session_info"] = info
    logging.info(
        "Host session attached [%s]: session=%r subject=%r",
        info.backend,
        info.session_name,
        info.subject,
    )


def evaluate_args(args_dict=None):
    """Evaluate parsed arguments."""
    args_dict["host_name"] = get_host_name()
    args_dict["host_ip"] = get_host_ip()
    args_dict["original"] = args_dict.copy()

    args_dict = _evaluate_log_level(args_dict=args_dict)
    args_dict = _evaluate_task(args_dict=args_dict)
    args_dict = _evaluate_metadata(args_dict=args_dict)
    setup_logging(
        level=args_dict["log_level"],
        log_file=args_dict["log_file"],
        task=args_dict.get("task", ""),
        subject=args_dict.get("subject", ""),
        setup=args_dict.get("setup", ""),
    )

    args_dict = _evaluate_and_load_configs(args_dict=args_dict)

    settings_task_default = args_dict["settings.task.default"]
    task_modes = read_task_modes(args_dict.get("config_file_task", ""))
    overlay_modes = read_task_modes(args_dict.get("config_file_task_overlay", ""))
    if overlay_modes:
        task_modes = {**task_modes, **overlay_modes}  # overlay mode definitions win

    if args_dict["command"] == "run":
        subject = args_dict["subject"]
        subject_config = args_dict.get("subject_config")
        if subject_config is None and subject != "_test_subject":
            if args_dict["debug"]:
                args_dict["subject"] = "_test_subject"
                logging.debug("Overwriting subject to _test_subject for debug mode")
            else:
                raise ValueError(
                    f"\n\n\tUnknown subject '{subject}'. Not found in "
                    f"{args_dict['config_dir']}/subjects/. "
                    f"Register first: murineshiftwork subject add -s {subject}\n"
                )
    else:
        raise ValueError(f"Unknown command: '{args_dict['command']}'")

    task_name = args_dict.get("task", "")
    patched = build_task_settings(
        task_name=task_name,
        settings_task_default=settings_task_default,
        task_modes=task_modes,
        subject_config=args_dict.get("subject_config"),
        task_mode=args_dict.get("task_mode", ""),
        cli_overrides=args_dict.get("task_settings_overrides", []),
        extra_injections=_extra_injections_from_args(args_dict),
    )
    args_dict["settings.task.patched"] = patched

    # Write task_mode back to subject YAML so next session picks up the same mode
    # without requiring --task-mode on the CLI again.
    task_mode = args_dict.get("task_mode", "")
    subject_config = args_dict.get("subject_config")
    if task_mode and subject_config and args_dict.get("config_dir") and task_name:
        try:
            save_subject_task_overrides(
                args_dict["config_dir"],
                args_dict["subject"],
                task_name,
                {"task_mode": task_mode},
            )
            logging.debug(
                f"Wrote task_mode '{task_mode}' to subject YAML for task '{task_name}'"
            )
        except Exception as exc:
            logging.warning(f"Could not write task_mode to subject YAML: {exc}")

    setup_config = args_dict.get("setup_config")
    _resolve_setup_config_ports(args_dict, setup_config, patched)
    _resolve_host_session(args_dict)
    subject_config = args_dict.get("subject_config")
    args_dict["execution_config"] = ExecutionConfig(
        setup=setup_config,
        subject=subject_config,
        task_name=task_name,
        task_settings=patched,
    )

    if args_dict.get("command") == "run":
        preflight_hardware_check(args_dict)

    from murineshiftwork.logic.log import json_dumps_type_safe

    logging.debug(
        "settings.task.patched:\n%s",
        json_dumps_type_safe(args_dict.get("settings.task.patched", {})),
    )

    return args_dict
