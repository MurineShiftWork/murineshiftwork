import logging
import time
from pathlib import Path

import yaml
from sshkeyboard import listen_keyboard
from sshkeyboard import stop_listening
from one_axis_stage.interface import MoveInterface
from one_axis_stage.controller import StageController

from murineshiftwork.logic.task_process import TaskProcess
from murineshiftwork.logic.task_process import TaskRunner


class KeyHandler:
    move_interface = None
    speed_mode = "slow"

    def __init__(self, move_interface=None):
        self.move_interface = move_interface

    def slow(self):
        return self.speed_mode == "slow"

    def set_speed(self, key=None):
        if key in "-_":
            self.speed_mode = "slow"
        elif key in "=+":
            self.speed_mode = "fast"
        print(f"Speed mode: {self.speed_mode}")

    def move_xy(self, key=None):
        if key == "w":
            self.move_interface.ym() if self.slow() else self.move_interface.ymm()
        elif key == "a":
            self.move_interface.xp() if self.slow() else self.move_interface.xpp()
        elif key == "s":
            self.move_interface.yp() if self.slow() else self.move_interface.ypp()
        elif key == "d":
            self.move_interface.xm() if self.slow() else self.move_interface.xmm()

    def move_z(self, key=None):
        if key == "up":
            self.move_interface.zp() if self.slow() else self.move_interface.zpp()
        elif key == "down":
            self.move_interface.zm() if self.slow() else self.move_interface.zmm()

    def press(self, key):
        print(f"KEY: {key}")
        if key in ["-", "_", "=", "+"]:
            self.set_speed(key=key)
        elif key in ["w", "a", "s", "d"]:
            self.move_xy(key=key)
        elif key in ["up", "down"]:
            self.move_z(key=key)
        elif key == "p":
            print(self.move_interface)
        elif key == "enter":
            stop_listening()
        else:
            print("-> Not actionable. Press 'enter' to exit.")


class Task(TaskRunner):
    def run(self):
        s = self.input_kwargs.get("settings.task.patched", {})
        serial_port_stage = self.input_kwargs.get("serial_port_stage", "") or s.get("serial_port_stage", "")
        calibration_file_stage = Path(s.get("calibration_file_stage", "")).expanduser()

        if calibration_file_stage.exists():
            with open(calibration_file_stage) as f:
                config = yaml.safe_load(f)
        elif s.get("settings.stage"):
            config = s["settings.stage"]
        else:
            logging.error("No stage config: set calibration_file_stage or configure a stage device in setup YAML")
            return

        config.setdefault("connection", {})["serial_port"] = serial_port_stage

        ctrl = StageController.from_config(config)
        move_interface = MoveInterface(ctrl, small_increment=20, large_increment=40)

        print("\n\tREADY FOR INPUTS !\n")
        listen_keyboard(
            on_press=KeyHandler(move_interface=move_interface).press,
            sequential=True,
            lower=True,
            delay_second_char=0.1,
        )
        ctrl.disconnect()


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
