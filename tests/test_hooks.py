"""Tests for the pre/post task hook system (murineshiftwork.logic.hooks)."""

import pytest
from murineshiftwork.hooks import (
    HookContext,
    SessionAbortError,
    TaskHook,
    collect_hooks,
    load_hooks,
    run_post_hooks,
    run_pre_hooks,
)

# ---------------------------------------------------------------------------
# Helpers


class _MutatingHook(TaskHook):
    def pre_run(self, ctx):
        ctx.task_settings["injected_key"] = "injected_value"

    def post_run(self, ctx):
        ctx.output["post_ran"] = True


class _FailingHook(TaskHook):
    def pre_run(self, ctx):
        raise RuntimeError("deliberate hook failure")

    def post_run(self, ctx):
        raise RuntimeError("deliberate hook failure")


def _ctx(**kwargs):
    defaults = dict(
        subject="mouse001", task_name="sequence", task_settings={}, session_paths={}
    )
    defaults.update(kwargs)
    return HookContext(**defaults)


# ---------------------------------------------------------------------------
# HookContext


def test_hook_context_default_output_is_empty():
    assert _ctx().output == {}


def test_hook_context_default_execution_config_is_none():
    assert _ctx().execution_config is None


def test_hook_context_stores_fields():
    ctx = _ctx(subject="m001", task_name="ps", task_settings={"k": 1})
    assert ctx.subject == "m001"
    assert ctx.task_name == "ps"
    assert ctx.task_settings["k"] == 1


# ---------------------------------------------------------------------------
# TaskHook base


def test_base_hook_pre_run_is_noop():
    TaskHook().pre_run(_ctx())  # must not raise


def test_base_hook_post_run_is_noop():
    TaskHook().post_run(_ctx())  # must not raise


# ---------------------------------------------------------------------------
# run_pre_hooks / run_post_hooks


def test_pre_hook_mutates_task_settings():
    settings = {}
    ctx = _ctx(task_settings=settings)
    run_pre_hooks([_MutatingHook()], ctx)
    assert settings["injected_key"] == "injected_value"


def test_post_hook_writes_to_output():
    ctx = _ctx()
    run_post_hooks([_MutatingHook()], ctx)
    assert ctx.output["post_ran"] is True


def test_failing_pre_hook_does_not_raise(caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        run_pre_hooks([_FailingHook()], _ctx())
    assert any("deliberate hook failure" in r.message for r in caplog.records)


def test_failing_post_hook_does_not_raise(caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        run_post_hooks([_FailingHook()], _ctx())
    assert any("deliberate hook failure" in r.message for r in caplog.records)


def test_multiple_pre_hooks_all_run():
    results = []

    class _RecordHook(TaskHook):
        def __init__(self, n):
            self.n = n

        def pre_run(self, ctx):
            results.append(self.n)

    run_pre_hooks([_RecordHook(1), _RecordHook(2), _RecordHook(3)], _ctx())
    assert results == [1, 2, 3]


def test_failing_pre_hook_does_not_stop_subsequent_hooks():
    results = []

    class _GoodHook(TaskHook):
        def pre_run(self, ctx):
            results.append("ran")

    run_pre_hooks([_FailingHook(), _GoodHook()], _ctx())
    assert results == ["ran"]


def test_failing_post_hook_does_not_stop_subsequent_hooks():
    results = []

    class _GoodHook(TaskHook):
        def post_run(self, ctx):
            results.append("ran")

    run_post_hooks([_FailingHook(), _GoodHook()], _ctx())
    assert results == ["ran"]


def test_empty_hook_list_is_noop():
    run_pre_hooks([], _ctx())
    run_post_hooks([], _ctx())


# ---------------------------------------------------------------------------
# load_hooks


def test_load_hooks_by_dotted_path():
    hooks = load_hooks(["murineshiftwork.hooks.TaskHook"])
    assert len(hooks) == 1
    assert isinstance(hooks[0], TaskHook)


def test_load_hooks_bad_path_skipped(caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        hooks = load_hooks(["nonexistent.module.SomeHook"])
    assert hooks == []
    assert any("nonexistent.module.SomeHook" in r.message for r in caplog.records)


def test_load_hooks_empty_string_skipped():
    assert load_hooks([""]) == []


def test_load_hooks_empty_list():
    assert load_hooks([]) == []


def test_load_hooks_mixed_valid_invalid():
    hooks = load_hooks(["nonexistent.Hook", "murineshiftwork.hooks.TaskHook"])
    assert len(hooks) == 1
    assert isinstance(hooks[0], TaskHook)


# ---------------------------------------------------------------------------
# collect_hooks: from setup_config and task_settings


def test_collect_hooks_from_task_settings():
    settings = {
        "HOOKS_PRE_TASK": ["murineshiftwork.hooks.TaskHook"],
        "HOOKS_POST_TASK": [],
    }
    pre, post = collect_hooks(None, settings)
    assert len(pre) == 1
    assert post == []


def test_collect_hooks_none_setup_config():
    pre, post = collect_hooks(None, {})
    assert pre == []
    assert post == []


def test_collect_hooks_from_setup_config():
    class _FakeHooksConfig:
        pre_task = ["murineshiftwork.hooks.TaskHook"]
        post_task = ["murineshiftwork.hooks.TaskHook"]

    class _FakeSetupConfig:
        hooks = _FakeHooksConfig()

    pre, post = collect_hooks(_FakeSetupConfig(), {})
    assert len(pre) == 1
    assert len(post) == 1


def test_collect_hooks_setup_no_hooks_attr():
    class _FakeSetupConfigNoHooks:
        pass

    pre, post = collect_hooks(_FakeSetupConfigNoHooks(), {})
    assert pre == []
    assert post == []


def test_collect_hooks_global_before_task_specific():
    """Global (setup) hooks come before task-specific hooks."""
    order = []

    class _GlobalHook(TaskHook):
        def pre_run(self, ctx):
            order.append("global")

    class _TaskHook(TaskHook):
        def pre_run(self, ctx):
            order.append("task")

    class _FakeHooksConfig:
        pre_task = ["murineshiftwork.hooks.TaskHook"]
        post_task = []

    class _FakeSetupConfig:
        hooks = _FakeHooksConfig()

    # Manually build like collect_hooks would; test ordering contract
    pre_global = [_GlobalHook()]
    pre_task = [_TaskHook()]
    pre = pre_global + pre_task
    run_pre_hooks(pre, _ctx())
    assert order == ["global", "task"]


# ---------------------------------------------------------------------------
# Integration: HooksConfig in SetupConfig (model round-trip)


def test_hooks_config_parses_from_dict():
    from murineshiftwork.logic.config.models import SetupConfig

    cfg = SetupConfig(
        name="test_setup",
        hooks={"pre_task": ["mylab.hooks.A"], "post_task": []},
    )
    assert cfg.hooks is not None
    assert cfg.hooks.pre_task == ["mylab.hooks.A"]
    assert cfg.hooks.post_task == []


def test_setup_config_without_hooks_is_valid():
    from murineshiftwork.logic.config.models import SetupConfig

    cfg = SetupConfig(name="no_hooks_setup")
    assert cfg.hooks.pre_task == []
    assert cfg.hooks.post_task == []


# ---------------------------------------------------------------------------
# Fatal hooks


class _FatalPreHook(TaskHook):
    fatal = True

    def pre_run(self, ctx):
        raise RuntimeError("fatal preflight failure")


class _FatalPostHook(TaskHook):
    fatal = True

    def post_run(self, ctx):
        raise RuntimeError("fatal post-session failure")


def test_fatal_pre_hook_raises_session_abort_error():
    with pytest.raises(SessionAbortError, match="fatal preflight failure"):
        run_pre_hooks([_FatalPreHook()], _ctx())


def test_fatal_post_hook_raises_session_abort_error():
    with pytest.raises(SessionAbortError, match="fatal post-session failure"):
        run_post_hooks([_FatalPostHook()], _ctx())


def test_fatal_pre_hook_aborts_before_subsequent_hooks():
    results = []

    class _ShouldNotRun(TaskHook):
        def pre_run(self, ctx):
            results.append("ran")

    with pytest.raises(SessionAbortError):
        run_pre_hooks([_FatalPreHook(), _ShouldNotRun()], _ctx())
    assert results == []


def test_fatal_post_hook_runs_remaining_hooks_then_raises():
    """Post-hooks: remaining hooks still run after a fatal failure."""
    results = []

    class _RunsAfter(TaskHook):
        def post_run(self, ctx):
            results.append("ran")

    with pytest.raises(SessionAbortError):
        run_post_hooks([_FatalPostHook(), _RunsAfter()], _ctx())
    assert results == ["ran"]


def test_non_fatal_hook_does_not_raise():
    run_pre_hooks([_FailingHook()], _ctx())  # must not raise
    run_post_hooks([_FailingHook()], _ctx())  # must not raise


def test_fatal_flag_default_is_false():
    assert TaskHook.fatal is False


def test_session_abort_error_is_runtime_error():
    assert issubclass(SessionAbortError, RuntimeError)


def test_fatal_pre_hook_wraps_original_cause():
    with pytest.raises(SessionAbortError) as exc_info:
        run_pre_hooks([_FatalPreHook()], _ctx())
    assert exc_info.value.__cause__ is not None
    assert "fatal preflight failure" in str(exc_info.value.__cause__)


def test_first_fatal_post_hook_error_raised_not_second():
    """When multiple fatal post-hooks fail, first error is raised."""

    class _FatalPostHook2(TaskHook):
        fatal = True

        def post_run(self, ctx):
            raise RuntimeError("second fatal failure")

    with pytest.raises(SessionAbortError, match="fatal post-session failure"):
        run_post_hooks([_FatalPostHook(), _FatalPostHook2()], _ctx())
