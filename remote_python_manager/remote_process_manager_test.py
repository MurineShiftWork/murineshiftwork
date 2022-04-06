import fabric

hostname = "rpi-81"
command = " for i in 1; do while : ; do : ; done & done  "

c = fabric.Connection(hostname)
res = c.run(f"{command} > /dev/null 2>&1 & echo $!", hide=True)
pid_exe = res.stdout.strip("\n").strip("\r")

print("PID:", pid_exe)

command = "/home/pi/miniconda3/envs/py36/bin/rcc_acquisition "

command = "pgrep rcc_acquisition"

c = fabric.Connection(hostname)
res = c.run(f"{command}", hide=True)
pid_pgrep = res.stdout.strip("\n").strip("\r")

print("PID:", pid_pgrep)

command = f"kill -9 {pid_pgrep}"


class RemoteProcessDispatcher:
    def __init__(self):
        super(RemoteProcessDispatcher, self).__init__()
