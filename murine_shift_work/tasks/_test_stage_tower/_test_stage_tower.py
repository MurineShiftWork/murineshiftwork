import logging
import time

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from sshkeyboard import listen_keyboard
from sshkeyboard import stop_listening

from murine_shift_work.logic.task_process import TaskProcess
from murine_shift_work.logic.task_process import TaskRunner

# import keyboard


class Task(TaskRunner):
    def run(self):
        # max_time = 1000
        # dt = time.time()
        # while not (time.time()-dt > max_time):

        # while True:
        #     event = keyboard.read_event()
        #     if event.event_type == keyboard.KEY_DOWN:
        #         key = event.name
        #         print(f"Pressed: {key}")
        #         if key == "q":
        #             break

        # from pynput.keyboard import Key, Listener
        #
        # def on_press(key):
        #     # print('{0} pressed'.format(
        #     # key))
        #     check_key(key)
        #
        # def on_release(key):
        #     # print('{0} release'.format(
        #     # key))
        #     if key == Key.esc:
        #         # Stop listener
        #         return False
        #
        # def check_key(key):
        #     if key in [Key.up, Key.down, Key.left, Key.right]:
        #         print("YES")
        #
        # # Collect events until released
        # with Listener(on_press=on_press, on_release=on_release) as listener:
        #     listener.join()

        def press(key):
            print(f"KEY: {key}")

            if key in "-_=+":
                if key in "-_":
                    pass  # small step
                elif key in "=+":
                    pass  # large step
                else:
                    raise ValueError(key)

            elif key in "wasd":
                pass  # move in plane: x,y

            elif key in ["up", "down"]:
                pass  # move z axis

            elif key == "enter":
                stop_listening()

            else:
                print("->Key not actionable.")

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
