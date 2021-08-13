import time
from multiprocessing import Queue

try:
    from rpi_camera_colony.control.conductor import Conductor
except ImportError:
    raise ImportError(
        "Requested video recording, but could not import 'rpi_camera_colony' package."
    )


from murine_shift_work import settings
from pathlib import Path

# from murine_shift_work.logic.misc import get_session_file_basename
from rpi_camera_colony.control.process_sandbox import ConductorAsProcess

kill_queue = Queue()

camera_config_file = Path(settings.__file__).parent / "camera.rcc.config"
acquisition_name = Path("testtesttest")  # get_session_file_basename(bpod=bpod)

# acquisition_name = get_session_file_basename(bpod=bpod)

conductor_args = {
    "config_file": str(camera_config_file),
    "acquisition_name": f"{'testsubject'}__{acquisition_name.name}",
}
video_process = ConductorAsProcess(
    controller_args=conductor_args, interrupt_queue=kill_queue
)
video_process.start()
time.sleep(10)

kill_queue.put(True)
# video_process.join(timeout=0)
print(" ")
