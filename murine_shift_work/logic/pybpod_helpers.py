def patch_user_settings():
    """Patch local user settings into configuration for main pybpod modules."""
    from confapp import conf

    conf += "murine_shift_work.settings.user_settings"
