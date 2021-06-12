import logging
import time
from multiprocessing import Queue
from pathlib import Path

import numpy as np
from confapp import conf as confsett
from pybpodapi.protocol import Bpod

from murine_shift_work.tasks.probabilistic_switching import task_settings
from murine_shift_work.tasks.probabilistic_switching.online_plotting import (
    OnlinePlottingForPS,
)
from murine_shift_work.tasks.probabilistic_switching.task_objects import TaskControl
from murine_shift_work.tools.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)


# GENERAL
bpod = Bpod()
subject_name = eval(confsett.PYBPOD_SUBJECTS[0])[0]
session_name = f"{subject_name}__{Path(confsett.PYBPOD_SESSION).name}"
print(session_name)
kill_queue = Queue()

# VIDEO
record_video = task_settings.RECORD_VIDEO
if False:  # record_video:
    try:
        from rpi_camera_colony.control.conductor import Conductor
    except ImportError:
        raise ImportError(
            "Requested video recording, but could not import 'rpi_camera_colony' package."
        )

    from murine_shift_work import calibration_data
    from pathlib import Path
    from murine_shift_work.tools.misc import get_session_file_basename

    camera_config_file = Path(calibration_data.__file__).parent / "camera.config"
    acquisition_name = get_session_file_basename(bpod=bpod)

    from rpi_camera_colony.control.process_sandbox import ConductorAsProcess

    conductor_args = {
        "config_file": str(camera_config_file),
        "acquisition_name": session_name,
    }
    video_process = ConductorAsProcess(
        controller_args=conductor_args, interrupt_queue=kill_queue
    )
    video_process.start()
else:
    video_conductor = None
    logging.info("NO VIDEO RECORDING.")

# PLOTS
show_plots = task_settings.SHOW_ONLINE_PLOTTING
if show_plots:
    data_queue = Queue()

    plotting_process = OnlinePlottingForPS(
        session_name=session_name,
        is_simulation=False,
        data_queue=data_queue,
        kill_queue=kill_queue,
    )
    plotting_process.start()
else:
    logging.info("NO ONLINE PLOTTING")
    data_queue = None

# TASK
task_control = TaskControl(bpod=bpod)
bpod.softcode_handler_function = task_control.softcode_handler

for trial_index in np.arange(task_settings.N_MAX_TRIALS):
    logging.info(f"Trial: {trial_index}")

    if trial_index == 0 and not task_settings.TESTING:
        sma = make_protocol_identifier_ttl_sequence(
            bpod=bpod,
            sequence=task_settings.TTL_IDENTIFIER_SEQUENCE,
            output_chanel_pulse=Bpod.OutputChannels.BNC2,
        )
    else:
        sma = task_control.draw_next_trial()

    bpod.send_state_machine(sma)

    if not bpod.run_state_machine(sma):
        logging.warning(
            f"No data returned on trial #{trial_index}. Terminating protocol."
        )
        break

    trial_data = bpod.session.current_trial.export()
    task_control.update(trial_index=trial_index, trial_data=trial_data)
    if show_plots and trial_index > 0:
        data_queue.put(
            {
                "trial_index": task_control.trial_index,
                "moving_average": task_control.moving_average.avg,
                "block_probability_left": task_control.probability_left,
                "block_probability_right": task_control.probability_right,
                "choice": task_control.last_choice,
                "rewarded": task_control.last_rewarded,
                "was_stop": task_control.last_stop,
                "punished": task_control.last_punish,
            }
        )

task_control.save()
bpod.close()

if show_plots or record_video:
    kill_queue.put(True)
    if record_video:
        video_process.join(0)

print("THE END.")


if __name__ == "__main__":
    print("main")
