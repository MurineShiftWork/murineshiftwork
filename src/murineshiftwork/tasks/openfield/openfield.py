from murineshiftwork.tasks.periodic_trigger_with_video.periodic_trigger_with_video import (
    run_task as run_task_core,
)


def run_task(**args_dict):
    run_task_core(**args_dict)


if __name__ == "__main__":
    print("main")
