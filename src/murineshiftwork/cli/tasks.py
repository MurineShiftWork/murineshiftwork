"""msw tasks subcommand handlers: list, defaults, init-configs."""

import importlib
import logging
import shutil
import sys
from importlib.metadata import entry_points
from pathlib import Path

import yaml

from murineshiftwork.logic.machine_config import resolve_config_dir

# ---------------------------------------------------------------------------
# Task discovery


def list_available_tasks(detailed=False):
    """Return available task names.

    Bundled tasks are discovered by filesystem scan — no registration needed.
    External task packages register via the ``msw.tasks`` entry-point group;
    those are merged in additively (bundled tasks take precedence on name clash).

    detailed=True returns {name: task_dir_path} instead of a list of names.
    """
    result = _list_tasks_filesystem(detailed=True)

    for ep in entry_points(group="msw.tasks"):
        if ep.name not in result:
            try:
                mod = importlib.import_module(ep.value)
                assert mod.__file__ is not None
                result[ep.name] = Path(mod.__file__).parent
            except Exception:
                logging.debug("msw.tasks entry point %r failed to load", ep.name)

    return result if detailed else sorted(result.keys())


def _list_tasks_filesystem(detailed=False):
    """Filesystem scan fallback — used when no msw.tasks entry points are registered."""
    try:
        import murineshiftwork.tasks as _tasks_pkg

        tasks_dir = (
            Path(_tasks_pkg.__path__[0]) if hasattr(_tasks_pkg, "__path__") else None
        )
    except ImportError:
        tasks_dir = None

    if tasks_dir is None or not tasks_dir.exists():
        try:
            import murineshiftwork

            tasks_dir = Path(list(murineshiftwork.__path__)[0]) / "tasks"
        except ImportError:
            return {} if detailed else []

    summary = {}
    for item in sorted(tasks_dir.iterdir()):
        if (
            item.is_dir()
            and (
                not item.name.startswith("_")
                or item.name.startswith("_test_")
                or item.name.startswith("_calibration_")
            )
            and (item / f"{item.name}.py").exists()
        ):
            summary[item.name] = item

    return summary if detailed else list(summary.keys())


def find_task_by_name(task_name=None, ignore_error=True):
    available_tasks = list_available_tasks()
    if task_name in available_tasks:
        return task_name
    found = [x for x in available_tasks if task_name in x]
    if len(found) == 1:
        return found[0]
    if len(found) == 0:
        return None
    msg = f"Task name '{task_name}' matches multiple tasks: {sorted(found)} — selecting {sorted(found)[0]}"
    logging.debug(msg)
    if ignore_error:
        return sorted(found)[0]
    raise ValueError(msg)


def load_task_module(task_name: str):
    """Import the module for a task, using entry points when available."""
    eps = {ep.name: ep for ep in entry_points(group="msw.tasks")}
    if task_name in eps:
        return importlib.import_module(eps[task_name].value)
    return importlib.import_module(f"murineshiftwork.tasks.{task_name}.{task_name}")


# ---------------------------------------------------------------------------
# Subcommand handlers


def _task_yaml_path(task_name: str) -> Path:
    mod = load_task_module(task_name)
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
