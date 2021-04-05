import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import proplot as plot
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from pybpod_tools.tasks.probabilistic_switching import task_settings
from pybpod_tools.tools.sounds import Sounds
from pybpod_tools.tools.specific_state_machines import add_trial_onset_ttl


class TaskControl(object):
    bpod = None
    valve_times_dict = {
        1: 50,
        2: 45,
        3: 30,
        4: 47,
    }  # None # FIXME: load from calibration
    sound = None

    def __init__(self, bpod=None):
        super(TaskControl, self).__init__()

        if not bpod:
            raise ValueError("required input argument: bpod")
        self.bpod = bpod

        self.sound = Sounds()

    #     FIXME: load valve times from calibration file

    def draw_next_block(self):
        pass

    def draw_next_trial(self):
        # check if block switch -> update probabilities

        # make SMA
        sma = self.make_state_machine()
        return sma

    def make_state_machine(self):
        output_actions__center_ready = [
            (Bpod.OutputChannels.PWM2, task_settings.HARDWARE_PORT_LIGHT_INTENSITY)
        ]
        state_duration__center_delay = task_settings.DELAY_UNTIL_CENTER_INIT
        output_actions__center_delay = output_actions__center_ready
        output_actions__side_ready = [
            (Bpod.OutputChannels.PWM1, task_settings.HARDWARE_PORT_LIGHT_INTENSITY),
            (Bpod.OutputChannels.PWM3, task_settings.HARDWARE_PORT_LIGHT_INTENSITY),
        ]
        state_duration__side_ready = task_settings.DELAY_UNTIL_SIDE_TIMEOUT
        state_duration__final = task_settings.STATE_DURATION_FINAL

        # SMA
        sma = StateMachine(bpod=self.bpod)
        sma = add_trial_onset_ttl(
            sma=sma,
            ttl_pulse_duration=task_settings.TTL_PULSE_DURATION,
            bnc_channel=eval(
                f"Bpod.OutputChannels.BNC{task_settings.HARDWARE_BNC_TRIAL_START}"
            ),
            next_state="center_ready",
        )

        # TRIAL
        sma.add_state(
            state_name="center_ready",
            state_timer=60,
            state_change_conditions={Bpod.Events.Port2In: "center_delay"},
            output_actions=output_actions__center_ready,
        )
        # INIT long enough -> proceed. pulled out too early -> back to center_ready
        sma.add_state(
            state_name="center_delay",
            state_timer=state_duration__center_delay,
            state_change_conditions={
                Bpod.Events.Port2Out: "center_ready",  # ABORTED
                Bpod.Events.Tup: "side_ready",
            },  # CONTINUE
            output_actions=output_actions__center_delay,
        )
        # TRAVEL to side -> wait for entry
        give_stop_signal = False

        if give_stop_signal:
            # TODO:  give stop signal sound -> contingency will be no reward for the ports

            # TODO: add state before side_ready to drop soft_code for sound
            sma.add_state(
                state_name="side_ready",
                state_timer=state_duration__side_ready,
                state_change_conditions={
                    Bpod.Events.Port1In: "choice_left",
                    Bpod.Events.Port3In: "choice_right",
                },
                output_actions=output_actions__side_ready,
            )
        else:
            sma.add_state(
                state_name="side_ready",
                state_timer=state_duration__side_ready,
                state_change_conditions={
                    Bpod.Events.Port1In: "choice_left",
                    Bpod.Events.Port3In: "choice_right",
                },
                output_actions=output_actions__side_ready,
            )

        choice_outcome_left = 0  # 0=unrewarded, 1=rewarded, -1=punish with air
        choice_outcome_right = 0  # 0=unrewarded, 1=rewarded, -1=punish with air

        if choice_outcome_left > 0:
            pass  # TODO: give reward
        elif choice_outcome_left < 0:
            pass  # TODO: punish with air
        else:  # == 0
            pass  # TODO: no outcome

        if choice_outcome_right > 0:
            pass  # TODO: give reward
        elif choice_outcome_right < 0:
            pass  # TODO: punish with air
        else:  # == 0
            pass  # TODO: no outcome

        valve_left_water = 0.04

        sma.add_state(
            state_name="choice_left",
            state_timer=valve_left_water,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=[(Bpod.OutputChannels.Valve, 1)],
        )
        sma.add_state(
            state_name="choice_right",
            state_timer=valve_left_water,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=[(Bpod.OutputChannels.Valve, 3)],
        )

        sma.add_state(
            state_name="final",
            state_timer=state_duration__final,
            state_change_conditions={
                Bpod.Events.Port1Out: "exit",
                Bpod.Events.Port2Out: "exit",
                Bpod.Events.Port3Out: "exit",
                Bpod.Events.Tup: "exit",
            },
            output_actions=[],
        )

        return sma

    def softcode_handler(self, softcode=None):
        self.sound.soft_code_handler_function(softcode=softcode)

    def update_task_progress(self, task_data=None):
        if not task_data:
            raise ValueError("No task data, although trial ran !?")
        pass


class TaskData(object):
    data = []
    save_path = None

    def __init__(self, save_path=None):
        super(TaskData, self).__init__()

        if not save_path:
            raise ValueError("required input argument: save_path")

        self.save_path = str(save_path)

    def append(self, trial_data):
        self.data.append(
            trial_data
        )  # TODO: make list of  for output data, then save as csv

    def save(self):
        data = pd.DataFrame(data=self.data)
        data.to_csv(self.save_path)


class OnlinePlotting(object):
    save_path = None
    save_fig_ext = ".eps"
    save_fig_param = {"dpi": 400}

    figure = None
    axes = None

    def __init__(self, save_path=None):
        super(OnlinePlotting, self).__init__()

        self.save_path = os.path.splitext(save_path)[0]

        self.figure, self.axes = plot.subplots(ncols=1, nrows=2)

    def update(self, task_data=None):
        print("here plotting")
        plt.plot(np.random.random(), np.random.random(), "k+")
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        self.figure.canvas.draw_idle()
        plt.pause(0.001)

    def save(self):
        self.figure.savefig(self.save_path + self.save_fig_ext, **self.save_fig_param)

    def bpod_loop_handler(self):
        self.figure.canvas.flush_events()
