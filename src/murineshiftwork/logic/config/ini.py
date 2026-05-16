import logging
from pathlib import Path

import yaml


def read_config(file=None, unrepr=True):
    if not Path(file).exists():
        raise FileNotFoundError(str(file))

    path = Path(file)
    if path.suffix not in (".yaml", ".yml"):
        return {}
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    # New format: params live under 'default:'; modes under 'mode:'
    # Legacy flat format (no 'default' key): return as-is for backward compat
    if "default" in raw:
        return raw["default"]
    return raw


def read_task_modes(file=None) -> dict:
    """Return the 'mode:' section from a task.yaml, or {} if absent or not YAML."""
    if not file or not Path(file).exists():
        return {}
    path = Path(file)
    if path.suffix not in (".yaml", ".yml"):
        return {}
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("mode", {})


def validate_config_file_path(
    config_file=None,
    default_dir=None,
):
    if not config_file:
        return ""
    config_file = Path(config_file)
    if config_file.exists():
        logging.debug(f"Found config file: {str(config_file)}")
        return str(config_file)
    else:
        if len(config_file.parts) == 1:
            default_dir = Path(default_dir)
            if (default_dir / config_file).exists():
                logging.debug(
                    f"Found config file: {str(default_dir / config_file)}"
                )
                return str(default_dir / config_file)
            else:
                logging.debug(
                    f"(1) File '{str(config_file)}' does not exist on its own or in default location at '{str(default_dir)}'"
                )
                return ""
        else:
            logging.debug(
                f"(2) File '{str(config_file)}' does not exist on its own or in default location at '{str(default_dir)}'"
            )
            return ""
