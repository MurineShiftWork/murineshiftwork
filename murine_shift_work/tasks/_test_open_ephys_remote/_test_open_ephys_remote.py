"""
    Test remote acquisition control of Open Ephys GUI via Network Events

    https://open-ephys.github.io/gui-docs/User-Manual/Plugins/Network-Events.html
    https://github.com/open-ephys/plugin-GUI/tree/master/Resources/Python
    https://github.com/open-ephys/open-ephys-python-tools
"""
import os
import time

import zmq


def run_client():
    """This function is testing the network feature.
    All code in this example taken from:
    https://github.com/open-ephys/plugin-GUI/blob/master/Resources/Python/record_control_example_client.py
    """
    # Basic start/stop commands
    start_cmd = "StartRecord"
    stop_cmd = "StopRecord"

    # Example settings
    session_name = "_test_subject__20210918_000000__ephys__multibehaviour"
    rec_dir = os.path.join("E:\OE_DATA\LBR", session_name)
    print("Saving data to:", rec_dir)

    # Some commands
    commands = [
        start_cmd + " RecDir=%s" % rec_dir,
        start_cmd + " PrependText=some_session_name. AppendText=.ephys",
        start_cmd + " PrependText=Session01 AppendText=Condition02",
        start_cmd + " PrependText=Session02 AppendText=Condition01",
        start_cmd,
        start_cmd + " CreateNewDir=1",
    ]

    # Connect network handler
    ip = "192.168.100.48"  # "127.0.0.1"
    ip = "172.24.242.219"  # "127.0.0.1"
    port = 5558
    timeout = 1.0

    url = "tcp://%s:%d" % (ip, port)

    with zmq.Context() as context:
        with context.socket(zmq.REQ) as socket:
            socket.RCVTIMEO = int(timeout * 1000)  # timeout in milliseconds
            socket.connect(url)

            # Start data acquisition
            socket.send_string("StartAcquisition")
            print(socket.recv())
            # time.sleep(5)

            socket.send_string("IsAcquiring")
            print("IsAcquiring:", socket.recv())
            print("")

            for start_cmd in commands:

                for cmd in [start_cmd, stop_cmd]:
                    socket.send_string(cmd)
                    print(socket.recv())

                    if "StartRecord" in cmd:
                        # Record data for 5 seconds
                        socket.send_string("IsRecording")
                        print("IsRecording:", socket.recv())

                        socket.send_string("GetRecordingPath")
                        print("Recording path:", socket.recv())

                        time.sleep(5)
                    else:
                        # Stop for 1 second
                        socket.send_string("IsRecording")
                        print("IsRecording:", socket.recv())
                        time.sleep(1)

                print("")

            # Finally, stop data acquisition; it might be a good idea to
            # wait a little bit until all data have been written to hard drive
            time.sleep(0.5)
            socket.send_string("StopAcquisition")
            print(socket.recv())


if __name__ == "__main__":
    run_client()
