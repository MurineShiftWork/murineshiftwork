import logging
from multiprocessing import Queue

import numpy as np
from pybpodapi.protocol import Bpod

from shift_work.tasks.probabilistic_switching import task_settings
from shift_work.tasks.probabilistic_switching.online_plotting import (
    OnlinePlottingForPS,
)
from shift_work.tasks.probabilistic_switching.task_objects import TaskControl
from shift_work.tools.specific_state_machines import (
    make_protocol_identifier_ttl_sequence,
)


bpod = Bpod()

if task_settings.RECORD_VIDEO:
    try:
        from rpi_camera_colony.control.conductor import AcquisitionConductor
    except ImportError:
        raise ImportError("")

show_plots = True
if show_plots:
    data_queue = Queue()
    kill_queue = Queue()

    from confapp import conf as confsett

    plotting_process = OnlinePlottingForPS(
        session_name=f"{eval(confsett.PYBPOD_SUBJECTS[0])[0]} @ {confsett.PYBPOD_SESSION}",
        is_simulation=False,
        data_queue=data_queue,
        kill_queue=kill_queue,
    )
    plotting_process.start()
else:
    data_queue = None
    kill_queue = None

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
            }
        )

task_control.save()
bpod.close()

if show_plots:
    kill_queue.put(True)

if __name__ == "__main__":
    print("main")
