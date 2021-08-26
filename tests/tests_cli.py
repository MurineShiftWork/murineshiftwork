import sys

from murine_shift_work.cli import run_cli
from murine_shift_work.logic.pybpod_helpers import patch_logging_levels

test_cases = {
    # "register_add_1": "register add -s _auto_test_1",
    "register_add_2": "register add -s _auto_test_2 -t minimal",
    # "register_add_3": "register add -s _auto_test_3 -t prob",
    # "register_remove_1": "register remove -s _auto_test_1",
    # "run_minimal_2_ok": "run -s _auto_test_2 -t minimal",
    # "run_minimal_3_not_registered": "run -s _auto_test_3 -t minimal",
    "register_rename_2": "register rename -s _auto_test_2 -n _auto_test_2_renamed --move-data",
    # "register_remove_2_old": "register remove -s _auto_test_2",
    "register_remove_2_new": "register remove -s _auto_test_2_renamed",
    # "register_remove_3": "register remove -s _auto_test_3_renamed",
}


if __name__ == "__main__":
    # for test_name, test_args in test_cases.items():
    #     args = sys.argv + test_args.split(" ")
    #     print("TEST:", test_name, args)
    #
    #     run_cli(*args)

    args = (
        sys.argv
        + "run -t video -d".split(" ")
    )
    run_cli(*args)
