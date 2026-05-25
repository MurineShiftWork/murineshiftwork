"""Tests for namespace.msw.yaml, msw_files, and TaskRunner.get_path()."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

_NAMESPACE_DIR = Path(__file__).parent.parent / "src" / "murineshiftwork" / "namespace"

_BASE = "/data/mouse_01/mouse_01__20260524_143022_123456__sequence/mouse_01__20260524_143022_123456__sequence"


# ---------------------------------------------------------------------------
# namespace.msw.yaml loads correctly


def test_msw_yaml_loads():
    from murineshiftwork.namespace.spec import NamespaceBuilder

    b = NamespaceBuilder.from_yaml(_NAMESPACE_DIR / "namespace.msw.yaml")
    assert b.spec.version == "1.0"
    assert b.hierarchy == ["session", "file"]


def test_msw_yaml_in_builder_suite():
    """namespace.msw.yaml is loadable alongside v1/v2/v3 specs."""
    from murineshiftwork.namespace.spec import NamespaceBuilder

    for name in ["v1", "v2", "v3", "msw"]:
        p = _NAMESPACE_DIR / f"namespace.{name}.yaml"
        assert p.exists(), f"Missing: {p}"
        b = NamespaceBuilder.from_yaml(p)
        assert b.hierarchy


# ---------------------------------------------------------------------------
# get_msw_builder() — lazy singleton


def test_get_msw_builder_returns_builder():
    from murineshiftwork.namespace.paths import get_msw_builder

    b = get_msw_builder()
    assert b.hierarchy == ["session", "file"]


def test_get_msw_builder_is_cached():
    from murineshiftwork.namespace.paths import get_msw_builder

    assert get_msw_builder() is get_msw_builder()


# ---------------------------------------------------------------------------
# build_path("file", ...) round-trip


@pytest.mark.parametrize(
    "artifact",
    ["session.yaml", "df.jsonl", "log", "jsonl", "plot_spec.yaml", "stimulation.json"],
)
def test_build_file_path_roundtrip(artifact):
    from murineshiftwork.namespace.paths import get_msw_builder

    b = get_msw_builder()
    values = {
        "subject": "mouse_01",
        "datetime": "20260524_143022_123456",
        "task": "sequence",
        "artifact": artifact,
    }
    fname = b.build_path("file", values)
    assert fname == f"mouse_01__20260524_143022_123456__sequence.msw.{artifact}"

    # extract round-trip
    extracted = b.extract_level_values("file", fname)
    assert extracted["artifact"] == artifact
    assert extracted["session"] == "mouse_01__20260524_143022_123456__sequence"


def test_build_file_legacy_datetime():
    from murineshiftwork.namespace.paths import get_msw_builder

    b = get_msw_builder()
    fname = b.build_path(
        "file",
        {
            "subject": "mouse_01",
            "datetime": "20210718_152153",
            "task": "probabilistic_switching",
            "artifact": "session.yaml",
        },
    )
    assert (
        fname == "mouse_01__20210718_152153__probabilistic_switching.msw.session.yaml"
    )


# ---------------------------------------------------------------------------
# msw_file()


def test_msw_file_produces_correct_path():
    from murineshiftwork.namespace.msw_files import msw_file

    p = msw_file(_BASE, "session.yaml")
    assert str(p) == _BASE + ".msw.session.yaml"
    assert isinstance(p, Path)


def test_msw_file_df_jsonl():
    from murineshiftwork.namespace.msw_files import msw_file

    p = msw_file(_BASE, "df.jsonl")
    assert str(p) == _BASE + ".msw.df.jsonl"


def test_msw_file_accepts_path_object():
    from murineshiftwork.namespace.msw_files import msw_file

    p = msw_file(Path(_BASE), "log")
    assert str(p) == _BASE + ".msw.log"


# ---------------------------------------------------------------------------
# is_msw_file()


def test_is_msw_file_true_for_session_yaml():
    from murineshiftwork.namespace.msw_files import is_msw_file

    assert is_msw_file(_BASE + ".msw.session.yaml")


def test_is_msw_file_true_for_df_jsonl():
    from murineshiftwork.namespace.msw_files import is_msw_file

    assert is_msw_file(_BASE + ".msw.df.jsonl")


def test_is_msw_file_false_for_plain_csv():
    from murineshiftwork.namespace.msw_files import is_msw_file

    assert not is_msw_file("/data/subject/session/something.csv")


def test_is_msw_file_false_for_no_separator():
    from murineshiftwork.namespace.msw_files import is_msw_file

    assert not is_msw_file("subject__20260524_143022_123456__task.jsonl")


# ---------------------------------------------------------------------------
# msw_artifact()


def test_msw_artifact_session_yaml():
    from murineshiftwork.namespace.msw_files import msw_artifact

    assert msw_artifact(_BASE + ".msw.session.yaml") == "session.yaml"


def test_msw_artifact_df_jsonl():
    from murineshiftwork.namespace.msw_files import msw_artifact

    assert msw_artifact(_BASE + ".msw.df.jsonl") == "df.jsonl"


def test_msw_artifact_raises_for_non_msw():
    from murineshiftwork.namespace.msw_files import msw_artifact

    with pytest.raises(ValueError, match="Not an MSW file"):
        msw_artifact("/data/something.csv")


# ---------------------------------------------------------------------------
# TaskRunner.get_path()


def test_taskrunner_get_path(tmp_path):
    from murineshiftwork.logic.task_process import TaskRunner

    session_file_path = str(
        tmp_path
        / "mouse_01"
        / "mouse_01__20260524_143022_123456__sequence"
        / "mouse_01__20260524_143022_123456__sequence"
    )

    runner = MagicMock(spec=TaskRunner)
    runner.input_kwargs = {"session_paths": {"session_file_path": session_file_path}}
    runner.get_path = TaskRunner.get_path.__get__(runner, TaskRunner)

    p = runner.get_path("df.jsonl")
    assert str(p) == session_file_path + ".msw.df.jsonl"
    assert isinstance(p, Path)


def test_taskrunner_get_path_session_yaml(tmp_path):
    from murineshiftwork.logic.task_process import TaskRunner

    session_file_path = str(
        tmp_path
        / "mouse_01"
        / "mouse_01__20260524_143022_123456__sequence"
        / "mouse_01__20260524_143022_123456__sequence"
    )

    runner = MagicMock(spec=TaskRunner)
    runner.input_kwargs = {"session_paths": {"session_file_path": session_file_path}}
    runner.get_path = TaskRunner.get_path.__get__(runner, TaskRunner)

    p = runner.get_path("session.yaml")
    assert p.name == "mouse_01__20260524_143022_123456__sequence.msw.session.yaml"
