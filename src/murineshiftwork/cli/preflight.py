"""Pre-flight hardware checks run before any session files are created."""

from pathlib import Path

from murineshiftwork.logic.misc import test_serial_port_is_accessible
from murineshiftwork.logic.paths import test_path_is_writable


def preflight_hardware_check(args_dict: dict) -> None:
    """Check devices and output dir before any session files are created.

    Raises RuntimeError listing ALL failing checks so the user can fix them at once.
    Skipped entirely when ``debug=True`` or subject is ``_test_subject``.
    """
    if (
        args_dict.get("simulate")
        or args_dict.get("debug")
        or args_dict.get("subject") == "_test_subject"
    ):
        return

    errors: list[str] = []
    setup_config = args_dict.get("setup_config")
    task_settings = args_dict.get("settings.task.patched", {})

    # --- Output directory writable ---
    out_path = Path(args_dict.get("out_path", ""))
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        errors.append(f"Cannot create output dir {out_path}: {exc}")
    else:
        write_test = out_path / ".msw_preflight_write_test"
        if not test_path_is_writable(write_test):
            errors.append(f"Output directory not writable: {out_path}")

    # --- Bpod ---
    bpod_port = args_dict.get("serial_port_bpod", "")
    if bpod_port and not test_serial_port_is_accessible(bpod_port):
        errors.append(f"Bpod serial port not accessible: {bpod_port!r}")

    # --- PulsePal (only if task requests stimulation or setup declares it) ---
    uses_stim = task_settings.get("use_stimulation", False)
    has_pulsepal_in_setup = setup_config and "pulsepal" in getattr(
        setup_config, "devices", {}
    )
    if uses_stim or has_pulsepal_in_setup:
        pp_port = task_settings.get("serial_port_pulsepal") or args_dict.get(
            "serial_port_pulsepal", ""
        )
        if pp_port and not test_serial_port_is_accessible(pp_port):
            errors.append(f"PulsePal serial port not accessible: {pp_port!r}")

    # --- Stage (if declared in setup) ---
    if setup_config and "stage" in getattr(setup_config, "devices", {}):
        try:
            stage_port = setup_config.device_port("stage")
        except ValueError:
            stage_port = task_settings.get("serial_port_stage") or args_dict.get(
                "serial_port_stage", ""
            )
        if stage_port and not test_serial_port_is_accessible(stage_port):
            errors.append(f"Stage serial port not accessible: {stage_port!r}")

    # --- Camera config file (if task records video) ---
    if task_settings.get("record_video", False):
        cam_cfg = args_dict.get("config_file_camera", "")
        if not cam_cfg or not Path(cam_cfg).exists():
            errors.append(f"Camera config not found: {cam_cfg!r}")

    if errors:
        bullet_list = "\n".join(f"  • {e}" for e in errors)
        raise RuntimeError(
            f"Pre-flight check failed — fix before session can start:\n{bullet_list}"
        )
