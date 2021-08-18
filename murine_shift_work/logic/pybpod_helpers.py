import logging


def patch_user_settings():
    """Patch local user settings into configuration for main pybpod modules."""
    from confapp import conf

    conf += "murine_shift_work.settings.user_settings"


def patch_logging_levels(target_level="WARNING"):
    for m in ["pybpodapi", "pybpodgui_api", "pybpodgui_plugin", "matplotlib"]:
        logger = logging.getLogger(m)
        logger.setLevel(target_level)


def get_subject_from_pybpod_conf():
    """Get subject name from pybpod configuration if exists (exists, when using GUI)."""
    from confapp import conf

    if len(conf.PYBPOD_SUBJECTS) == 0:
        raise ValueError(
            "\n\n\tNo subjects in GUI settings. Is this a CLI call with is_cli_call=False upstream ?\n\n"
        )
    else:
        return eval(conf.PYBPOD_SUBJECTS[0])[0]
