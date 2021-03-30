import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import proplot as plot
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine


class TaskControl(object):
    bpod = None

    MAX_TRIALS = 1500

    def __init__(self, bpod=None):
        super(TaskControl, self).__init__()

        if not bpod:
            raise ValueError("required input argument: bpod")
        self.bpod = bpod

    def next_block(self):
        pass

    def next_trial(self):
        sma = self.make_state_machine()
        return sma

    def play_go_cue(self):
        pass

    def play_stop_cue(self):
        pass

    def stop_sound(self):
        pass

    def make_state_machine(self):
        state_duration__ttl = 0.010  # 10 msec
        output_actions__ttl = {Bpod.OutputChannels.BNC2, 1}
        state_duration__center_delay = 0.15
        output_actions__center_delay = {}  # TODO: turn lights on
        state_duration__side_ready = 10  # timeout in sec
        state_duration__final = 2  # delay to allow port-out event

        sma = StateMachine(bpod=self.bpod)

        # TTL
        sma.add_state(
            state_name="ttl_on",
            state_timer=state_duration__ttl,
            state_change_conditions={Bpod.Events.Tup, "ttl_off"},
            output_actions=output_actions__ttl,
        )
        sma.add_state(
            state_name="ttl_off",
            state_timer=0,
            state_change_conditions={Bpod.Events.Tup, "center_ready"},
            output_actions=output_actions__ttl,
        )
        # TRIAL
        sma.add_state(
            state_name="center_ready",
            state_timer=0,
            state_change_conditions={Bpod.Events.Port2In, "center_delay"},
            output_actions={},  # TODO: add output action?
        )
        # INIT long enough -> proceed. pulled out too early -> back to center_ready
        sma.add_state(
            state_name="center_delay",
            state_timer=state_duration__center_delay,
            state_change_conditions={
                Bpod.Events.Port2Out,
                "center_ready",  # ABORTED
                Bpod.Events.Tup,
                "side_ready",
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
                    Bpod.Events.Port1In,
                    "choice_left",
                    Bpod.Events.Port3In,
                    "choice_right",
                },
                output_actions=output_actions__center_delay,
            )
        else:
            sma.add_state(
                state_name="side_ready",
                state_timer=state_duration__side_ready,
                state_change_conditions={
                    Bpod.Events.Port1In,
                    "choice_left",
                    Bpod.Events.Port3In,
                    "choice_right",
                },
                output_actions=output_actions__center_delay,
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

        sma.add_state(
            state_name="final",
            state_timer=state_duration__final,
            state_change_conditions={
                Bpod.Events.Port1Out,
                "exit",
                Bpod.Events.Port2Out,
                "exit",
                Bpod.Events.Port3Out,
                "exit",
                Bpod.Events.Tup,
                "exit",
            },
            output_actions={},
        )
        return sma

    def softcode_handler(self, code=None):
        if code == 0:
            pass  # some init tasks
        elif code == 1:
            self.play_go_cue()
        elif code == 2:
            self.play_stop_cue()
        elif code == -1:
            self.stop_sound()

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
