"""Module-load-time defaults for the CLI.

Factored out of evaluate.py so parser.py can import them without importing the
full evaluate pipeline, avoiding any risk of a circular dependency.
"""
from murineshiftwork.logic.machine_config import resolve_config_dir, resolve_data_dir
from murineshiftwork.logic.misc import list_available_tasks

default_out_path = resolve_data_dir()
default_config_dir = resolve_config_dir()
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
