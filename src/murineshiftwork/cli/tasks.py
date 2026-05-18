"""msw tasks subcommand handlers: list, defaults, init-configs."""

import shutil
import sys
from pathlib import Path

import yaml

from murineshiftwork.logic.machine_config import resolve_config_dir
from murineshiftwork.logic.misc import find_task_by_name, list_available_tasks


def _task_yaml_path(task_name: str) -> Path:
    import importlib

    mod = importlib.import_module(f"murineshiftwork.tasks.{task_name}.{task_name}")
    assert mod.__file__ is not None
    return Path(mod.__file__).parent / "task.yaml"


def run_tasks_list(filter="", config_dir="", **kwargs):
    all_tasks = list_available_tasks()
    if filter:
        all_tasks = [t for t in all_tasks if filter.lower() in t.lower()]

    main = sorted(t for t in all_tasks if not t.startswith("_"))
    calibration = sorted(t for t in all_tasks if t.startswith("_calibration"))
    tests = sorted(t for t in all_tasks if t.startswith("_test"))

    _config_dir = resolve_config_dir(cli_override=config_dir)
    overlay_dir = Path(_config_dir) / "tasks" if _config_dir else None

    for heading, group in (
        ("Tasks", main),
        ("Calibration", calibration),
        ("Tests", tests),
    ):
        if not group:
            continue
        print(f"\n{heading}:")
        for name in group:
            has_overlay = (
                " [overlay]"
                if overlay_dir and (overlay_dir / name / "task.yaml").exists()
                else ""
            )
            print(f"  {name}{has_overlay}")
    print()


def run_tasks_defaults(task="", **kwargs):
    if not task:
        print(
            "Error: task name required. Usage: msw tasks defaults <task_name>",
            file=sys.stderr,
        )
        sys.exit(1)

    name = find_task_by_name(task_name=task)
    if name is None:
        available = sorted(list_available_tasks())
        print(
            f"Error: no task matching '{task}'. Available:\n"
            + "\n".join(f"  {t}" for t in available),
            file=sys.stderr,
        )
        sys.exit(1)

    yaml_path = _task_yaml_path(name)
    if not yaml_path.exists():
        print(f"Error: no task.yaml found for '{name}' at {yaml_path}", file=sys.stderr)
        sys.exit(1)

    print(f"# {name}  —  {yaml_path}\n")
    print(yaml_path.read_text())


def run_tasks_modes(task="", **kwargs):
    if not task:
        print(
            "Error: task name required. Usage: msw tasks modes <task_name>",
            file=sys.stderr,
        )
        sys.exit(1)

    name = find_task_by_name(task_name=task)
    if name is None:
        available = sorted(list_available_tasks())
        print(
            f"Error: no task matching '{task}'. Available:\n"
            + "\n".join(f"  {t}" for t in available),
            file=sys.stderr,
        )
        sys.exit(1)

    yaml_path = _task_yaml_path(name)
    if not yaml_path.exists():
        print(f"Error: no task.yaml found for '{name}' at {yaml_path}", file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load(yaml_path.read_text()) or {}
    modes = data.get("mode") or {}

    if not modes:
        print(f"{name}: no named modes defined.")
        return

    print(f"\n{name} modes:\n")
    for mode_name, overrides in modes.items():
        if overrides:
            keys = ", ".join(sorted(overrides.keys()))
            print(f"  {mode_name:<30}  overrides: {keys}")
        else:
            print(f"  {mode_name}")
    print()


def run_tasks_init_configs(tasks=None, config_dir="", force=False, **kwargs):
    _config_dir = resolve_config_dir(cli_override=config_dir)
    if not _config_dir:
        print(
            "Error: config_dir not set. Run 'msw init <config_dir>' first or pass -cd.",
            file=sys.stderr,
        )
        sys.exit(1)

    all_tasks = list_available_tasks(detailed=True)
    target_names = tasks if tasks else list(all_tasks.keys())

    for name in target_names:
        resolved = find_task_by_name(task_name=name)
        if resolved is None or resolved not in all_tasks:
            print(f"  skip  {name}  (not found)")
            continue

        src = all_tasks[resolved] / "task.yaml"
        if not src.exists():
            print(f"  skip  {resolved}  (no bundled task.yaml)")
            continue

        dst = Path(_config_dir) / "tasks" / resolved / "task.yaml"
        if dst.exists() and not force:
            print(f"  skip  {resolved}  (exists — use --force to overwrite)")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        print(f"  wrote {resolved}  →  {dst}")
