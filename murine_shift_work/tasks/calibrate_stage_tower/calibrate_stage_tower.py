import logging
import shutil
import socket
import time
from pathlib import Path

import yaml
from sshkeyboard import listen_keyboard
from sshkeyboard import stop_listening
from stage_controller.move_interface import MoveInterface

from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner
from tests.stage_config import config_for_all_stages


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

        print(f"Speed mode switched to {self.speed_mode}")

    def move_xy(self, key=None):
        if key == "w":
            if self.slow():
                self.move_interface.ym()
            else:
                self.move_interface.ymm()
        elif key == "a":
            if self.slow():
                self.move_interface.xp()
            else:
                self.move_interface.xpp()
        elif key == "s":
            if self.slow():
                self.move_interface.yp()
            else:
                self.move_interface.ypp()
        elif key == "d":
            if self.slow():
                self.move_interface.xm()
            else:
                self.move_interface.xmm()

    def move_z(self, key=None):
        if key == "up":
            if self.slow():
                self.move_interface.zp()
            else:
                self.move_interface.zpp()
        elif key == "down":
            if self.slow():
                self.move_interface.zm()
            else:
                self.move_interface.zmm()

    def press(self, key):
        print(f"KEY: {key}")

        # MOVE
        if key in ["-", "_", "=", "+"]:
            self.set_speed(key=key)

        elif key in ["w", "a", "s", "d"]:
            self.move_xy(key=key)

        elif key in ["up", "down"]:
            self.move_z(key=key)

        # SET MIN/MAX
        elif key in ["u", "i", "o"]:
            print("Setting MAX position for axis:")
            # u/i/o for x/y/z MAX + j/k/l for x/y/z MIN
            if key == "u":
                self.move_interface.x.position_max = (
                    self.move_interface.x.position_raw
                )
                print(f"\tX -> {self.move_interface.x.position_raw}")

            elif key == "i":
                self.move_interface.y.position_max = (
                    self.move_interface.y.position_raw
                )
                print(f"\tY -> {self.move_interface.y.position_raw}")

            elif key == "o":
                self.move_interface.z.position_max = (
                    self.move_interface.z.position_raw
                )
                print(f"\tY -> {self.move_interface.z.position_raw}")

        elif key in ["j", "k", "l"]:
            print("Setting MIN position for axis:")
            # u/i/o for x/y/z MAX + j/k/l for x/y/z MIN
            if key == "j":
                self.move_interface.x.position_min = (
                    self.move_interface.x.position_raw
                )
                print(f"\tX -> {self.move_interface.x.position_raw}")

            elif key == "k":
                self.move_interface.y.position_min = (
                    self.move_interface.y.position_raw
                )
                print(f"\tY -> {self.move_interface.y.position_raw}")

            elif key == "l":
                self.move_interface.z.position_min = (
                    self.move_interface.z.position_raw
                )
                print(f"\tY -> {self.move_interface.z.position_raw}")

        # SET KNOWN
        elif key == "n":
            name = input("Position name:\t")
            print(name)
            self.move_interface.save_position_as_known(position_name=name)
            print(self.move_interface.known_positions)

        # SHOW CONFIG
        elif key == "p":
            print(self.move_interface)

        # EXIT & SAVE
        elif key == "enter":
            hostname = socket.gethostname()
            save_path = Path(
                f"~/.murineshiftwork/msw.debug.stage.config.{hostname}.yaml"
            ).expanduser()
            self.move_interface.write_config(
                config_path=save_path, overwrite=True
            )
            # todo: save config (including new known positions) to file for use with Task
            stop_listening()

        else:
            print("-> Key not actionable. Exit protocol by pressing 'enter'")


class Task(TaskRunner):
    def run(self):
        hostname = socket.gethostname()
        print(f"HOST: {hostname}")
        # task_settings = self.input_kwargs["settings.task.patched"]

        calibration_file_stage = Path(
            self.input_kwargs["calibration_file_stage"]
        ).expanduser()
        print(f"calibration_file_stage: {calibration_file_stage}")
        if not Path(calibration_file_stage).exists():
            from murine_shift_work import settings

            default_file = (
                Path(settings.__path__[0]) / "calibration.stage.default.yaml"
            )
            shutil.copyfile(default_file, calibration_file_stage)
            print(f"COPIED FILE: {default_file} TO {calibration_file_stage}")

        with open(calibration_file_stage, "r") as f:
            calibration_stage_dict = yaml.full_load(f.read())

        stage_config = calibration_stage_dict.get(hostname, "default")
        print(calibration_stage_dict.get(hostname, "default"))

        # axes_names = tuple(
        #     config_for_all_stages["stage_tower_setup_1"].get("axes").keys()
        # )
        axes_names = tuple(stage_config.get("axes").keys())
        serial_port_stage = self.input_kwargs.get(
            "serial_port_stage", "XX"
        )  # "/dev/ttyUSB0")
        # stage_config = config_for_all_stages[
        #     "stage_tower_setup_1"
        # ]  # todo: calibration_file_stage

        move_interface = MoveInterface(
            axes_names=axes_names,
            serial_port=serial_port_stage,
            stage_config=stage_config,
        )

        kh = KeyHandler(move_interface=move_interface)

        print("\n\tREADY FOR INPUTS !\n")
        listen_keyboard(
            on_press=kh.press,
            sequential=True,
            lower=True,
            delay_second_char=0.1,
        )

        calibration_stage_dict[hostname] = move_interface.config_dict()
        with open(calibration_file_stage, "w") as f:
            f.write(yaml.dump(calibration_stage_dict))


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
