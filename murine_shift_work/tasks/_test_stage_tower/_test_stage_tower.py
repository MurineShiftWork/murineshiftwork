import logging
import time

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from sshkeyboard import listen_keyboard
from sshkeyboard import stop_listening
from stage_controller.move_interface import MoveInterface

from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner
from tests.stage_config import config_for_all_stages


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

        def press(key):
            print(f"KEY: {key}")

            if key in "-_=+":
                if key in "-_":
                    pass  # TODO: small step

                elif key in "=+":
                    pass  # TODO: large step

                else:
                    raise ValueError(key)

            elif key in "wasd":
                if key == "w":
                    move_interface.ymm()
                elif key == "a":
                    move_interface.xpp()
                elif key == "s":
                    move_interface.ypp()
                elif key == "d":
                    move_interface.xmm()

                pass  # move in plane: x,y

            elif key in ["up", "down"]:
                if key == "up":
                    move_interface.zpp()
                elif key == "down":
                    move_interface.zmm()
                pass  # move z axis

            elif key == "k":
                name = input("Position name:\t")
                print(name)
                pass  # TODO: save position as known. ask a name for new position

            elif key == "enter":
                # todo: save config (including new known positions) to file for use with Task
                stop_listening()

            else:
                print(
                    "-> Key not actionable. Exit protocol by pressing 'enter'"
                )

        listen_keyboard(
            on_press=press, sequential=True, lower=True, delay_second_char=0.1
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
