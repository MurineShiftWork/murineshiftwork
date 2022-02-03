from murine_shift_work.tasks.periodic_trigger_with_video.periodic_trigger_with_video import (
    run_task as run_task_core,
)
from murine_shift_work.tasks.periodic_trigger_with_video.periodic_trigger_with_video import (
    Task,
)


def run_task(**args_dict):

    args_dict.update(
        {
            "ttl_identifier_sequence": "sLsLss",
            "trigger_iti": 5,
            "n_max_trials": 1500,
        }
    )
    run_task_core(**args_dict)


if __name__ == "__main__":
    print("main")
