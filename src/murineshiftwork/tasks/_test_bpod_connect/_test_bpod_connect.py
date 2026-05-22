import time

from murineshiftwork.logic.task_process import TaskProcess, TaskRunner

_MACHINE_NAMES = {1: "r0.5", 2: "r0.7", 3: "r2.0", 4: "r2+"}


def _info_box(pairs: list[tuple[str, str]]) -> None:
    """Print key: value pairs in a box, colons aligned."""
    key_w = max(len(k) for k, _ in pairs)
    lines = [f"{k:<{key_w}} : {v}" for k, v in pairs]
    width = max(len(line) for line in lines)
    bar = "+" + "-" * (width + 4) + "+"
    print(bar)
    for line in lines:
        print(f"|  {line:<{width}}  |")
    print(bar)


class Task(TaskRunner):
    def run(self):
        bpod = self.bpod
        hw = bpod._hardware
        mt = getattr(hw, "machine_type", None)
        fw = getattr(hw, "firmware_version", "?")

        pairs = [
            ("serial port", str(bpod.serial_port)),
            ("port config", str(getattr(bpod, "_port_config", "?"))),
            ("firmware version", str(fw)),
            ("machine type", _MACHINE_NAMES.get(mt, f"unknown ({mt})")),
            ("n global timers", str(getattr(hw, "n_global_timers", "?"))),
            ("n global counters", str(getattr(hw, "n_global_counters", "?"))),
            ("n conditions", str(getattr(hw, "n_conditions", "?"))),
            ("max serial events", str(getattr(hw, "max_serial_events", "?"))),
            ("max states", str(getattr(hw, "max_states", "?"))),
            ("cycle frequency", str(getattr(hw, "cycle_frequency", "?"))),
        ]
        print()
        _info_box(pairs)
        print()


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    run_task()
