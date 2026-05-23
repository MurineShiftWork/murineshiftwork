"""Pre/post task hook system.

Hooks run around every task session at two call-points:
  pre_run  — after Bpod connects, before TaskRunner.prepare(); may mutate task_settings
  post_run — in TaskProcess.__exit__, before Bpod disconnects; may read session output

Hook classes are referenced by dotted import path and instantiated at session start.

Error handling:
  fatal = False (default): a raising hook logs WARNING and is skipped; session continues.
  fatal = True:            a raising hook raises SessionAbortError; session is aborted.
                           Pre-hook abort: TaskProcess closes Bpod before propagating.
                           Post-hook abort: Bpod is closed, then exception propagates.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any


class SessionAbortError(RuntimeError):
    """Raised by a fatal hook to abort the session before it starts (pre) or after (post)."""


@dataclass
class HookContext:
    """Shared context passed to every hook method.

    Pre-hooks may write to ``task_settings`` — changes are seen by the task.
    Post-hooks may read ``output`` populated by task or other post-hooks.
    Both may stash state in ``output`` for other hooks to consume.
    """

    subject: str
    task_name: str
    task_settings: dict
    session_paths: dict
    execution_config: Any | None = None
    output: dict = field(default_factory=dict)


class TaskHook:
    """Base class for session hooks.  Override pre_run and/or post_run.

    Set ``fatal = True`` on the subclass to abort the session when the hook raises
    instead of logging a warning and continuing.  The Bpod connection is always closed
    cleanly before the SessionAbortError propagates.
    """

    fatal: bool = False

    def pre_run(self, ctx: HookContext) -> None:
        pass

    def post_run(self, ctx: HookContext) -> None:
        pass


def load_hooks(dotted_paths: list[str]) -> list[TaskHook]:
    """Import and instantiate hook classes from dotted import paths.

    Unknown / un-importable paths are logged as WARNING and skipped.
    """
    hooks: list[TaskHook] = []
    for path in dotted_paths:
        if not path:
            continue
        try:
            module_path, _, class_name = path.rpartition(".")
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            hooks.append(cls())
            logging.debug(f"Loaded hook: {path}")
        except Exception as exc:
            logging.warning(f"Could not load hook '{path}': {exc}")
    return hooks


def collect_hooks(
    setup_config: Any,
    task_settings: dict,
) -> tuple[list[TaskHook], list[TaskHook]]:
    """Collect pre and post hooks from setup config and task settings.

    Order: global (setup YAML) first, then task-specific (task settings).
    """
    pre_paths: list[str] = []
    post_paths: list[str] = []

    if (
        setup_config is not None
        and hasattr(setup_config, "hooks")
        and setup_config.hooks
    ):
        pre_paths.extend(setup_config.hooks.pre_task)
        post_paths.extend(setup_config.hooks.post_task)

    pre_paths.extend(task_settings.get("HOOKS_PRE_TASK") or [])
    post_paths.extend(task_settings.get("HOOKS_POST_TASK") or [])

    return load_hooks(pre_paths), load_hooks(post_paths)


def run_pre_hooks(hooks: list[TaskHook], ctx: HookContext) -> None:
    """Run pre-session hooks in order.

    Non-fatal failures log WARNING and are skipped.
    Fatal failures raise SessionAbortError (caller must clean up hardware).
    """
    if not hooks:
        return
    logging.info("Pre-hooks: %d to run", len(hooks))
    for hook in hooks:
        name = type(hook).__name__
        logging.info("Pre-hook: %s", name)
        try:
            hook.pre_run(ctx)
            logging.info("Pre-hook done: %s", name)
        except SessionAbortError:
            raise
        except Exception as exc:
            if getattr(hook, "fatal", False):
                raise SessionAbortError(
                    f"Fatal pre-hook {name} aborted session: {exc}"
                ) from exc
            logging.warning(
                f"Pre-hook {name} raised (skipped): {exc}",
                exc_info=True,
            )


def run_post_hooks(hooks: list[TaskHook], ctx: HookContext) -> None:
    """Run post-session hooks in order.

    Non-fatal failures log WARNING and are skipped.
    Fatal failures raise SessionAbortError after all remaining hooks have run.
    """
    if not hooks:
        return
    logging.info("Post-hooks: %d to run", len(hooks))
    first_fatal: SessionAbortError | None = None
    for hook in hooks:
        name = type(hook).__name__
        logging.info("Post-hook: %s", name)
        try:
            hook.post_run(ctx)
            logging.info("Post-hook done: %s", name)
        except SessionAbortError:
            raise
        except Exception as exc:
            if getattr(hook, "fatal", False):
                err = SessionAbortError(
                    f"Fatal post-hook {name} aborted session: {exc}"
                )
                err.__cause__ = exc
                if first_fatal is None:
                    first_fatal = err
            else:
                logging.warning(
                    f"Post-hook {name} raised (skipped): {exc}",
                    exc_info=True,
                )
    if first_fatal is not None:
        raise first_fatal
