"""Module-load-time defaults for the CLI.

Factored out of evaluate.py so parser.py can import them without importing the
full evaluate pipeline, avoiding any risk of a circular dependency.
"""

from pathlib import Path

from murineshiftwork.cli.tasks import list_available_tasks
from murineshiftwork.logic.machine_config import (
    resolve_config_dir,
    resolve_data_dir,
)

default_out_path = resolve_data_dir()
default_config_dir = resolve_config_dir()

CALIBRATION_FILE_PATH = Path("~/.murineshiftwork").expanduser()
DEFAULT_CALIBRATION_FILE_LIQUID = str(
    CALIBRATION_FILE_PATH / "calibration.liquid.default.csv"
)
DEFAULT_CALIBRATION_FILE_SOUND = "calibration.sound.default.csv"
DEFAULT_CALIBRATION_FILE_STAGE = str(
    CALIBRATION_FILE_PATH / "calibration.stage.default.yaml"
)


def _build_task_list() -> str:
    all_tasks = list_available_tasks()
    main = sorted(t for t in all_tasks if not t.startswith("_"))
    calibration = sorted(t for t in all_tasks if t.startswith("_calibration"))
    tests = sorted(t for t in all_tasks if t.startswith("_test"))
    lines = []
    for heading, group in (
        ("Tasks", main),
        ("Calibration", calibration),
        ("Tests", tests),
    ):
        lines.append(f"  {heading}:")
        lines.extend(f"    - {t}" for t in group)
    return "\n".join(lines)


available_tasks = _build_task_list()
