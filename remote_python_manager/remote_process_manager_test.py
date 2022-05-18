# import fabric
#
# hostname = "rpi-81"
# command = " for i in 1; do while : ; do : ; done & done  "
#
# c = fabric.Connection(hostname)
# res = c.run(f"{command} > /dev/null 2>&1 & echo $!", hide=True)
# pid_exe = res.stdout.strip("\n").strip("\r")
#
# print("PID:", pid_exe)
#
# command = "/home/pi/miniconda3/envs/py36/bin/rcc_acquisition "
#
# command = "pgrep rcc_acquisition"
#
# c = fabric.Connection(hostname)
# res = c.run(f"{command}", hide=True)
# pid_pgrep = res.stdout.strip("\n").strip("\r")
#
# print("PID:", pid_pgrep)
#
# command = f"kill -9 {pid_pgrep}"
import fabric


def str_to_pid(value):
    """"""
    assert isinstance(value, str)

    for replace in ["\n", "\r"]:
        stdout = value.replace(replace, "")

    try:
        return int(stdout)
    except TypeError:
        return None


class DispatchHandler:
    """"""

    command = ""
    hostname = ""
    detach = False
    ask_for_pid = False
    auto_connect = True
    terminate_on_del = True

    host_connection = None
    process_name = None
    dispatch_reply = None  # todo: dict ?
    _pid = None

    def __init__(
        self,
        command: str = None,
        hostname: str = None,
        detach: bool = False,
        ask_for_pid: bool = False,
        auto_connect: bool = True,
        terminate_on_del: bool = True,
        **kwargs,
    ):
        """

        :param command:
        :param hostname:
        :param detach:
        :param ask_for_pid:
        :param auto_connect:
        :param terminate_on_del:
        :param kwargs:
        """
        super(DispatchHandler, self).__init__()

        assert isinstance(command, str)

        self.command = command
        self.hostname = hostname
        self.detach = detach
        self.ask_for_pid = ask_for_pid
        self.auto_connect = auto_connect
        self.terminate_on_del = terminate_on_del
        self.process_name = command.split(" ")[0]

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        if auto_connect:
            self._connect()

    @property
    def pid(self):
        return self._pid

    @pid.setter
    def pid(self, value=None):
        self._pid = str_to_pid(value=value)

    def _connect(self):
        """Connect host with fabric. This allows use of ssh hostnames/host aliases in addition to plain IP addresses."""
        self.host_connection = fabric.Connection(self.hostname)
        return self.host_connection

    def _run_command(
        self,
        command=None,
        detach=False,
        ask_for_pid=False,
    ):
        """"""
        assert command is not None

        run_str = " ".join(
            [
                f"{command}",
                f"{'> /dev/null 2>&1' if detach else ''}",
                f"{'& echo $!' if ask_for_pid else ''}",
            ]
        )
        reply = self.host_connection.run(run_str, hide=True)

        if ask_for_pid:
            self.pid = reply.stdout

        return reply

    def dispatch(self):
        """"""
        self.dispatch_reply = self._run_command(
            command=self.command, detach=True, ask_for_pid=True
        )
        return self.dispatch_reply

    def _get_remote_pid(self):
        """"""
        reply = self._run_command(command=f"pgrep {self.process_name}")
        return str_to_pid(reply.stdout)

    def remote_exists(self):
        """"""
        if self.pid is None:
            return None

        return self.pid == self._get_remote_pid()

    def terminate(self):
        """"""
        if self.pid is not None and self.remote_exists():
            self._run_command(command=f"kill -9 {self.pid}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.terminate_on_del:
            self.terminate()

    def __del__(self):
        if self.terminate_on_del:
            self.terminate()


class ProcessExecutor:
    def __init__(
        self,
    ):
        super(ProcessExecutor, self).__init__()

        # todo: add zmq comms, logging handler etc.


class ProcessManager:
    dispatch_handler = None

    def __init__(
        self,
    ):
        super(ProcessManager, self).__init__()

        # todo: add ProcessDispatcher
        self.dispatch_handler = DispatchHandler()
        # todo: add zmq comms -> thread to run io loop ??


class CommsServer:
    def __init__(self, sub_address=None, pub_address=None):
        super(CommsServer, self).__init__()

        # todo: make proxy for pub/sub pattern
        # todo: add thread for io loop
