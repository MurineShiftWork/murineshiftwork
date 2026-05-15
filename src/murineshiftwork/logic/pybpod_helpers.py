def patch_user_settings():
    """Patch local user settings into configuration for main pybpod modules."""
    from confapp import conf

    conf += "murineshiftwork.settings.user_settings"
