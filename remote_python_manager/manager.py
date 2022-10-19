"""

general remote process instantiator

takes
    remote python interpreter path
    remote python script
    OR
    remote python CLI entrypoint in a specific interpreter environment (absolute path if not in default environment)

    arguments for script / entrypoint

    process management
        forward remote STDOUT/STDERR locally to local STDOUT/ERR = bool

##

more specific remote process manager for murine-shift-work

Local MSW entrypoint
    arg: remote_execution = True -> requires IP address and communication port to deal with remote commands / logging

    makes: RemoteExecutor
        arg: gets all local args for paradigm forwarded
        return: logging/paradigm updates via zmq -> display progress locally if selected to show data from Task

    main design question: let remote handle hardware (RCC, bpod, pulsepal)?
        bpod needs to be attached to remote for processing of trial updates in Task
        pulsepal should also be attached remotely for easier hardware architecture (together with bpod)
        RCC can be remotely or locally instantiated. Would be easy to do locally as is also zmq based communication



nohup python3 -u <script> </dev/null >/dev/null 2>&1 &

( nohup python3 -u <script> & )
python3 -u <script> </dev/null &>/dev/null & disown


cmd = ssh $REMOTE_NAME ( nohup $PYTHON_PATH $PYTHON_CMD_OR_MODULE </dev/null >/dev/null 2>&1 & )

subprocess.Popen(cmd, stdout, stderr, stdin)
"""
import time


class ManagedRemoteProcess:
    def __init__(
        self,
        socket_address=None,
        socket_port=None,
    ):

        super(ManagedRemoteProcess, self).__init__()

        self._open_comms()

    def _open_comms(self):
        # connect zmq socket listener for instructions + sending log/debug/feedback info
        # set `message_handler` as callback for receiver

        # Requires 1x SUB for incoming, 1x PUB for publishing
        pass

    def message_handler(self, message=None):
        NotImplementedError(
            "To be overwritten in subclass to handle messages from comms socket"
        )


class SomeRemoteTask(ManagedRemoteProcess):
    def __init__(self, specific_remote_kwargs=None, **kwargs):
        super(SomeRemoteTask, self).__init__()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def message_handler(self, message=None):
        message_header, message_content = message.split(".")
        if "start" in message_header:
            self.start(**message_content)
        elif "random_other_command" in message_header:
            self.random_other_command(data="whatever")
        else:
            print("Command not implemented")

        NotImplementedError(
            "TODO. For example, tells acquisition to start/stop/update settings"
        )

    def start(self, **kwargs):
        pass  # whatever is to be started

    def stop(self):
        pass

    def update(self, update_info=None):
        pass

    def random_other_command(self, data=None):
        pass


class RemoteProcessHandler:
    remote_entrypoint_name = None
    remote_entrypoint_kwargs = {}

    def __init__(
        self,
        remote_entrypoint_name: str = None,
        remote_entrypoint_kwargs: dict = None,
    ):
        super(RemoteProcessHandler, self).__init__()
        self.remote_entrypoint_name = remote_entrypoint_name
        self.remote_entrypoint_kwargs = remote_entrypoint_kwargs  # have to be preprended with dash/double-dash for CLI

    def _open_comms(self):
        pass  # local comms: PUB socket to communicate with remote process

    def dispatch(self):
        # launch new process via ssh to remote
        # subprocess call has to contain everything to disconnect stdin/stdout/stderr
        """
        cmd = ssh $REMOTE_NAME ( nohup $PYTHON_PATH $PYTHON_CMD_OR_MODULE </dev/null >/dev/null 2>&1 & )

        """
        return self  # return self, so that can be chained as: obj = Class().dispatch()

    def shutdown(self, timeout=1):
        # instruct remote to shut down. If no reply in timeout window, kill via ssh pkill
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def send_command(self, cmd=None):
        pass  # send command to remote


"""
WORKFLOW:

1) Dispatch SomeRemoteTask based on ManagedRemoteProcess via ssh subprocess nohup call
2) From local process, send instructions to SomeRemoteTask
"""

if __name__ == "__main__":
    # LOCAL
    remote_handler = RemoteProcessHandler(
        remote_entrypoint_name="remote_entrypoint_cli",
        remote_entrypoint_kwargs={},
    )
    remote_handler.dispatch()  # -> See below for remote code executing now ...

    remote_handler.send_command()  # e.g. start acquisition
    time.sleep(1)

    remote_handler.shutdown()

    # REMOTE
    # - enter CLI
    cli_kwargs = {}

    # - run SomeRemoteTask
    with SomeRemoteTask(**cli_kwargs) as spec:
        time.sleep(10)
