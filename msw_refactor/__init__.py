import logging
import os
import subprocess
from pathlib import Path

import pyzmq as zmq


class Hardware:
    def __init__(self):
        super(Hardware, self).__init__()


class Bpod(Hardware):
    def __init__(self):
        super(Bpod, self).__init__()


class PulsePal(Hardware):
    def __init__(self):
        super(PulsePal, self).__init__()


class TaskExecutor:
    def __init__(self):
        super(TaskExecutor, self).__init__()


class TaskProcess:
    def __init__(self):
        super(TaskProcess, self).__init__()
        # - zmq socket to publish stuff for remote process

    def start(self):
        pass

    def pause(self):
        pass

    def stop(self):
        pass

    def _start_remote(self):
        ssh_command = "ssh"
        address = "localhost"
        python_interpreter = "python"
        command = "murine_shift_work -h"
        arg_list = [ssh_command, address, command]
        answer = subprocess.Popen(
            arg_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )


def run_task(**kwargs):
    task_process = TaskProcess()

    task_process.start()


if __name__ == "__main__":
    kwargs = {}
    run_task(**kwargs)
