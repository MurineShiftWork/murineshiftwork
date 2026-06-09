"""Reader tests against checked-in task-specific session fixtures.

Fixtures (tests/data/):
  fixture_sequence/       — _test_subject, setup-npx2, 2026-05-20
                            65 task trials + 1 barcode trial, v2 YAML format.
                            Fields include: level, outcome, poke_events,
                            water_ul_trial (old name — back-compat test).
  fixture_fixedsubjects/  — _test_subject, 2026-05-18
                            6 task trials + 2 barcode trials, v2 YAML format.
                            Fields include: choice, rewarded, block_number.
  fixture_optotagging/    — _test_subject, 2026-05-27, ephys parent session.
                            Two subprotocols in session_manifest.yaml:
                            power_ramp_1mw (complete, has JSONL) and
                            power_ramp_2mw (aborted, JSONL absent).
                            Merged df contains only power_ramp_1mw rows.

These tests always run (no skip guard).
"""

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "data"
FIXTURE_SEQ = FIXTURES_DIR / "fixture_sequence"
FIXTURE_FSUB = FIXTURES_DIR / "fixture_fixedsubjects"
FIXTURE_OPTO_ACQ = FIXTURES_DIR / "fixture_optotagging"
FIXTURE_OPTO_SESSION = (
    FIXTURE_OPTO_ACQ / "_test_subject__20260527_133053_901389__optotagging"
)


def _skip_if_absent(path):
    return pytest.mark.skipif(not path.exists(), reason=f"fixture absent: {path}")


# ---------------------------------------------------------------------------
# Sequence task fixture
# ---------------------------------------------------------------------------


@_skip_if_absent(FIXTURE_SEQ)
class TestSequenceFixture:
    def test_loads_without_error(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        assert isinstance(d, dict)

    def test_is_complete(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        assert d["is_complete_session"] is True

    def test_task_name(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        assert d["settings.process"]["task"] == "sequence"

    def test_df_is_dataframe(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        assert isinstance(d["df"], pd.DataFrame)

    def test_df_has_task_trials(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        df = d["df"]
        task_rows = df[df["trial_type"] == "task"]
        assert len(task_rows) >= 5

    def test_df_sequence_fields_present(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        df = d["df"]
        task_rows = df[df["trial_type"] == "task"]
        for field in ("level", "outcome", "poke_events"):
            assert field in task_rows.columns, (
                f"expected column '{field}' missing from df"
            )

    def test_df_has_barcode_trial(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        df = d["df"]
        barcode_rows = df[df["trial_type"] == "barcode"]
        assert len(barcode_rows) >= 1

    def test_settings_task_has_sequence_key(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        ts = d["settings.task"]
        assert ts is not None
        assert "sequence" in ts

    def test_not_legacy(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        assert d["is_legacy_session"] is False

    def test_msw_version_present(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_SEQ)
        assert d["msw_version"] not in ("unknown", "legacy", "")


# ---------------------------------------------------------------------------
# probabilistic_switching_fixedsubjects fixture
# ---------------------------------------------------------------------------


@_skip_if_absent(FIXTURE_FSUB)
class TestFixedSubjectsFixture:
    def test_loads_without_error(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        assert isinstance(d, dict)

    def test_is_complete(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        assert d["is_complete_session"] is True

    def test_task_name(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        assert d["settings.process"]["task"] == "probabilistic_switching_fixedsubjects"

    def test_df_is_dataframe(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        assert isinstance(d["df"], pd.DataFrame)

    def test_df_has_task_trials(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        df = d["df"]
        task_rows = df[df["trial_type"] == "task"]
        assert len(task_rows) >= 5

    def test_df_fixedsubjects_fields_present(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        df = d["df"]
        task_rows = df[df["trial_type"] == "task"]
        for field in ("choice", "rewarded", "block_number"):
            assert field in task_rows.columns, (
                f"expected column '{field}' missing from df"
            )

    def test_settings_task_has_hardware_keys(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        ts = d["settings.task"]
        assert ts is not None
        assert "HARDWARE_BNC_TRIAL_START" in ts

    def test_settings_stage_present(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        assert "settings.stage" in d, "stage section expected in fixedsubjects sessions"

    def test_not_legacy(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        assert d["is_legacy_session"] is False

    def test_msw_version_present(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_FSUB)
        assert d["msw_version"] not in ("unknown", "legacy", "")


# ---------------------------------------------------------------------------
# Optotagging fixture — ephys parent session + multi-protocol loading
# ---------------------------------------------------------------------------


@_skip_if_absent(FIXTURE_OPTO_SESSION)
class TestOptotaggingFixture:
    def test_loads_without_error(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert isinstance(d, dict)

    def test_is_ephys_session(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert d["is_ephys_session"] is True

    def test_settings_ephys_backend(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert d["settings.ephys"]["backend"] == "open_ephys"

    def test_task_name(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert d["settings.process"]["task"] == "optotagging"

    def test_df_is_dataframe(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert isinstance(d["df"], pd.DataFrame)

    def test_df_has_subprotocol_column(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert "subprotocol" in d["df"].columns

    def test_df_contains_only_available_subprotocols(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        # power_ramp_2mw has no JSONL in the fixture (aborted, only CSV present)
        assert set(d["df"]["subprotocol"].unique()) == {"power_ramp_1mw"}

    def test_subprotocols_metadata_present(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert d["subprotocols"] is not None
        assert len(d["subprotocols"]) == 2

    def test_subprotocols_metadata_has_barcode_fields(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        sp = d["subprotocols"][0]
        assert sp["name"] == "power_ramp_1mw"
        assert sp["barcode_start"] == 130617617295

    def test_not_legacy(self):
        from murineshiftwork.readers.session import read_session_data

        d = read_session_data(session_dir=FIXTURE_OPTO_SESSION)
        assert d["is_legacy_session"] is False
