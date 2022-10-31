import logging
import time

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

        if key in ["-", "_", "=", "+"]:
            self.set_speed(key=key)

        elif key in ["w", "a", "s", "d"]:
            self.move_xy(key=key)

        elif key in ["up", "down"]:
            self.move_z(key=key)

        elif key == "k":
            name = input("Position name:\t")
            print(name)
            pass  # TODO: save position as known. ask a name for new position

        elif key == "p":
            print(self.move_interface)

        elif key == "enter":
            # todo: save config (including new known positions) to file for use with Task
            stop_listening()

        else:
            print("-> Key not actionable. Exit protocol by pressing 'enter'")


class Task(TaskRunner):
    def run(self):
        axes_names = tuple(
            config_for_all_stages["stage_tower_setup_1"].get("axes").keys()
        )
        serial_port = "/dev/ttyUSB0"
        stage_config = config_for_all_stages["stage_tower_setup_1"]

        move_interface = MoveInterface(
            axes_names=axes_names,
            serial_port=serial_port,
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


def run_task(**kwargs):
    with TaskProcess(**kwargs) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
