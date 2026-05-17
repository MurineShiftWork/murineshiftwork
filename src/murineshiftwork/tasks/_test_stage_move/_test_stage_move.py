import logging
import time

import yaml
from one_axis_stage.controller import StageController
from one_axis_stage.interface import MoveInterface
from sshkeyboard import listen_keyboard, stop_listening

from murineshiftwork.logic.config import update_stage_config
from murineshiftwork.logic.task_process import TaskProcess, TaskRunner


class KeyHandler:
    move_interface = None
    ctrl = None
    speed_mode = "slow"
    config_dir = None
    setup_name = None

    def __init__(self, move_interface=None, config_dir=None, setup_name=None):
        self.move_interface = move_interface
        self.ctrl = move_interface.controller
        self.config_dir = config_dir
        self.setup_name = setup_name

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
            print("-> Y-")
            self.move_interface.ym() if self.slow() else self.move_interface.ymm()
        elif key == "a":
            print("-> X+")
            self.move_interface.xp() if self.slow() else self.move_interface.xpp()
        elif key == "s":
            print("-> Y+")
            self.move_interface.yp() if self.slow() else self.move_interface.ypp()
        elif key == "d":
            print("-> X-")
            self.move_interface.xm() if self.slow() else self.move_interface.xmm()

    def move_z(self, key=None):
        if key == "up":
            print("-> Z+")
            self.move_interface.zp() if self.slow() else self.move_interface.zpp()
        elif key == "down":
            print("-> Z-")
            self.move_interface.zm() if self.slow() else self.move_interface.zmm()

    def _save_to_setup(self):
        if self.config_dir and self.setup_name:
            update_stage_config(
                config_dir=self.config_dir,
                setup_name=self.setup_name,
                stage_controller_config=self.ctrl.config,
            )
            print(f"Saved stage config to setup '{self.setup_name}'")
        else:
            logging.warning(
                "No config_dir/setup_name — cannot write back to setup YAML"
            )

    def press(self, key):
        print(f"KEY: {key}")

        if key in ["-", "_", "=", "+"]:
            self.set_speed(key=key)

        elif key in ["w", "a", "s", "d"]:
            self.move_xy(key=key)

        elif key in ["up", "down"]:
            self.move_z(key=key)

        # SET MAX position for x/y/z
        elif key in ["u", "i", "o"]:
            axis_map = {"u": "x", "i": "y", "o": "z"}
            axis_name = axis_map[key]
            if axis_name in self.ctrl.axes:
                axis = self.ctrl.axes[axis_name]
                axis.get_info()
                axis.position_max = axis.position_raw
                print(f"Set {axis_name.upper()} max -> {axis.position_raw}")

        # SET MIN position for x/y/z
        elif key in ["j", "k", "l"]:
            axis_map = {"j": "x", "k": "y", "l": "z"}
            axis_name = axis_map[key]
            if axis_name in self.ctrl.axes:
                axis = self.ctrl.axes[axis_name]
                axis.get_info()
                axis.position_min = axis.position_raw
                print(f"Set {axis_name.upper()} min -> {axis.position_raw}")

        # SAVE current position as a named known position
        elif key == "n":
            import datetime

            name = datetime.datetime.now().strftime("pos_%Y%m%d_%H%M%S")
            self.ctrl.save_as_known_position(position_name=name)
            print(
                f"Saved known position '{name}': {self.ctrl.known_positions.get(name)}"
            )

        # PRINT full config (refreshes live positions from hardware first)
        elif key == "space":
            for axis in self.ctrl.axes.values():
                axis.get_info()
            print(yaml.dump(self.ctrl.config, default_flow_style=False))

        # PING axes and print live info
        elif key == "p":
            for name, axis in self.ctrl.axes.items():
                info = axis.get_info()
                print(f"{name}: {info}")

        # EXIT and SAVE to setup YAML
        elif key == "enter":
            self._save_to_setup()
            stop_listening()

        # EXIT without saving
        elif key == "backspace":
            print("Exiting without saving.")
            stop_listening()

        else:
            print(
                "-> Not actionable. [enter]=save+exit  [backspace]=exit  [space]=print config"
            )


class Task(TaskRunner):
    def run(self):
        s = self.input_kwargs.get("settings.task.patched", {})
        serial_port_stage = s.get("serial_port_stage", "")
        config = s.get("settings.stage")
        calibrate_mode = s.get("calibrate", False)

        config_dir = self.input_kwargs.get("config_dir", "")
        setup_name = self.input_kwargs.get("setup", "")

        if not config or not config.get("axes"):
            logging.error(
                "No stage config with axes: configure a stage device with axes in setup YAML"
            )
            return

        if calibrate_mode:
            for axis_cfg in config["axes"].values():
                axis_cfg["position_min"] = 1
                axis_cfg["position_max"] = 999
            print(
                "\n\t[CALIBRATION MODE] Limits set to 1-999. Use u/i/o to set max, j/k/l to set min.\n"
            )

        config.setdefault("connection", {})["serial_port"] = serial_port_stage
        ctrl = StageController.from_config(config)
        move_interface = MoveInterface(ctrl, small_increment=20, large_increment=40)

        print("\n\tREADY FOR INPUTS !")
        print(
            "\twasd=XY  arrows=Z  +/-=speed  space=config  p=ping  u/i/o=set max  j/k/l=set min"
        )
        print("\tn=save position  enter=save+exit  backspace=exit\n")

        kh = KeyHandler(
            move_interface=move_interface,
            config_dir=config_dir,
            setup_name=setup_name,
        )
        listen_keyboard(
            on_press=kh.press,
            sequential=True,
            lower=True,
            delay_second_char=0.1,
        )


def run_task(**kwargs):
    with TaskProcess(**kwargs, require_bpod=False) as tp:
        while tp.is_running():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                tp.stop_task()


if __name__ == "__main__":
    print("main")
