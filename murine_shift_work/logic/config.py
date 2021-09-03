from pathlib import Path
from shutil import copyfile
from rich import get_console
from configobj import ConfigObj


def read_config(file=None, unrepr=True):
    if not Path(file).exists():
        raise FileNotFoundError(str(file))

    return ConfigObj(infile=str(file), unrepr=unrepr, list_values=True).dict()


def write_config(
    in_dict=None, save_path=None, do_backup_original=True, backup_extension="bak"
):
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
