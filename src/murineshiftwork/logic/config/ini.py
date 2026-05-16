import logging
from pathlib import Path
from shutil import copyfile

import yaml


def read_config(file=None, unrepr=True):
    if not Path(file).exists():
        raise FileNotFoundError(str(file))

    path = Path(file)
    if path.suffix in (".yaml", ".yml"):
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

    # Legacy INI format (subject.settings files in msw_configs)
    from configobj import ConfigObj
    return ConfigObj(infile=str(path), unrepr=unrepr, list_values=True).dict()


def write_config(
    in_dict=None,
    save_path=None,
    do_backup_original=True,
    backup_extension="bak",
):
    from configobj import ConfigObj
    new_config = ConfigObj(in_dict, unrepr=True, list_values=True)
    save_path = str(save_path)

    if do_backup_original:
        dst = ".".join([str(save_path), backup_extension])
        copyfile(src=save_path, dst=dst)

        if not Path(dst).exists():
            raise FileNotFoundError(
                f"Config backup not found at {dst} after copying from {save_path}"
            )

    new_config.filename = save_path
    new_config.write()

    if not Path(new_config.filename).exists():
        raise FileNotFoundError(f"Config file not found at {save_path}")


def validate_config_file_path(
    config_file=None,
    default_dir=None,
):
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
