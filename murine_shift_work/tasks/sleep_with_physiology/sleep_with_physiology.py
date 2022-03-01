from murine_shift_work.remote_ephys import make_parser_remote_ephys
from murine_shift_work.remote_ephys import run_remote_ephys
from murine_shift_work.tasks.periodic_trigger_with_video.periodic_trigger_with_video import (
    run_task as run_task_core,
)
from murine_shift_work.tasks.periodic_trigger_with_video.periodic_trigger_with_video import (
    Task,
)


def run_task(**args_dict):

    # FIXME: add Intan recording around sleep time
    #  - extract required input args from: make_parser_remote_ephys
    #  - run via: run_remote_ephys

    trigger_iti = 5
    max_runtime = 7200  # seconds

    args_dict.update(
        {
            "ttl_identifier_sequence": "sLsLss",
            "trigger_iti": trigger_iti,
            "max_runtime": max_runtime,
        }
    )
    run_task_core(**args_dict)


if __name__ == "__main__":
    print("main")
