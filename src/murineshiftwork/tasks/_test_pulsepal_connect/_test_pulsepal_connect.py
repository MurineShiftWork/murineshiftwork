import time

from pypulsepal import PulsePal as _PulsePal

from murineshiftwork.logic.task_process import TaskProcess, TaskRunner

_MODEL_NAMES = {1: "model-1 (fw<20)", 2: "model-2 (fw>=20)"}


def _info_box(pairs: list[tuple[str, str]]) -> None:
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
        devices = self.input_kwargs.get("devices") or {}
        settings = self.input_kwargs.get("settings.task.patched") or {}

        handle = devices.get("pulsepal")
        _owns = handle is None

        if handle is None:
            port = settings.get("serial_port_pulsepal", "/dev/ttyACM1")
            handle = _PulsePal(serial_port=port)

        pairs = [
            ("serial port", str(handle.serial_port)),
            ("firmware version", str(handle.firmware_version)),
            ("model", _MODEL_NAMES.get(handle.model, f"unknown ({handle.model})")),
            ("dac bit max", str(handle.dac_bitMax)),
            ("cycle frequency", str(handle.cycle_frequency)),
            ("output channels", str(handle.nr_output_channels)),
            ("trigger channels", str(handle.nr_trigger_channels)),
        ]
        print()
        _info_box(pairs)
        print()

        if _owns:
            handle.close()


def run_task(**kwargs):
    with TaskProcess(require_bpod=False, **kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    run_task()
