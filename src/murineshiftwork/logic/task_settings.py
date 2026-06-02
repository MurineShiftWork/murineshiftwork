"""Pure function for building the resolved task-settings dict.

Priority chain (lowest → highest):
  1. bundled task.yaml default:
  2. config_dir overlay task.yaml default: (already merged into settings_task_default before call)
  3. task_mode overrides from subject YAML task_overrides (sticky mode)
  4. subject YAML task_overrides (non-mode keys)
  5. CLI --task-mode (overrides sticky mode from subject YAML)
  6. CLI -ts KEY=VALUE overrides
"""

import ast
import json
import logging
from typing import Any


def parse_key_value_list(kv_list: list) -> dict:
    """Parse ['KEY=VALUE', ...] into a dict with type coercion."""
    result = {}
    for item in kv_list:
        item = item.strip().strip("'\"")
        if "=" not in item:
            continue
        k, _, v = item.partition("=")
        k = k.strip()
        v = v.strip()
        try:
            result[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            result[k] = v
    return result


def build_task_settings(
    task_name: str,
    settings_task_default: dict,
    task_modes: dict,
    subject_config: Any = None,
    task_mode: str = "",
    cli_overrides: list | None = None,
    extra_injections: dict | None = None,
) -> dict:
    """Return the fully resolved task-settings dict.

    Args:
        task_name: canonical task name (used to look up subject YAML overrides).
        settings_task_default: merged bundled + overlay defaults (already deep-merged).
        task_modes: dict of mode_name → override_dict from task.yaml mode: section.
        subject_config: SubjectConfig instance or None.
        task_mode: effective --task-mode string (CLI value; empty string = no override).
        cli_overrides: list of 'KEY=VALUE' strings from -ts (highest priority).
        extra_injections: keys injected only if not already present in the resolved dict
            (e.g. calibration paths, config_dir, settings.stage).
    """
    from murineshiftwork.logic.config import deep_merge

    patched = dict(settings_task_default)

    subject_yaml_patch = (
        dict(subject_config.task_overrides.get(task_name, {})) if subject_config else {}
    )

    # Sticky task_mode: read from subject YAML unless CLI --task-mode overrides it
    sticky_mode = subject_yaml_patch.pop("task_mode", "")
    effective_mode = task_mode or sticky_mode

    if effective_mode:
        if effective_mode not in task_modes:
            raise ValueError(
                f"Task mode '{effective_mode}' not found in task.yaml 'mode:' section. "
                f"Available: {list(task_modes.keys())}"
            )
        mode_overrides = task_modes[effective_mode]
        patched = deep_merge(patched, mode_overrides)
        logging.debug(f"Task mode '{effective_mode}' applied: {mode_overrides}")

    if subject_yaml_patch:
        patched = deep_merge(patched, subject_yaml_patch)
        logging.debug(
            f"Subject YAML task_overrides for '{task_name}': {subject_yaml_patch}"
        )

    resolved_overrides = parse_key_value_list(cli_overrides or [])
    patched.update(resolved_overrides)
    if resolved_overrides:
        logging.debug(f"CLI task-settings overrides applied: {resolved_overrides}")

    if patched:
        logging.debug(
            f"settings.task.patched for '{task_name}':\n"
            + json.dumps(patched, indent=4, sort_keys=True, default=str)
        )

    for key, value in (extra_injections or {}).items():
        if key not in patched:
            patched[key] = value

    return patched
