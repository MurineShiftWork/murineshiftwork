import logging
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pyqtgraph as pg
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from pybpod_tools.tasks.probabilistic_switching import task_settings
from pybpod_tools.tools.calibration_handling import get_calibration_point_for_valve
from pybpod_tools.tools.calibration_handling import get_sound_delay_correction_value
from pybpod_tools.tools.maths import withprob
from pybpod_tools.tools.misc import get_session_file_basename
from pybpod_tools.tools.sounds import Sounds
from pybpod_tools.tools.specific_state_machines import add_trial_onset_ttl


class TaskControl(object):
    bpod = None
    sound = None

    save_path_data = None

    block_number = 0
    block_trial_number = 0
    trial_number = 0
    reward_number = 0
    tau = 8
    # block length range: 25 - 45
    min_block_length = 25
    min_trials_post_criterion = 10
    mean_neutral_block_length = 35
    criterion_contrast_blocks = 0.8
    criterion_neutral_blocks = 0.6
    criterion_tau = None  # fixme: implement decay fct
    criterion_block_switch_reached = False
    block_hazard_rate = 1 / (mean_neutral_block_length - min_block_length)

    # probabilities = [[k, k[::-1]] for k in itertools.combinations_with_replacement([10,50,90],2)]
    # probabilities = [item for subl in probabilities for item in subl]
    probabilities = [
        # (10, 10),
        # (10, 10),
        (10, 50),
        (50, 10),
        (10, 90),
        (90, 10),
        # (50, 50),
        (50, 50),
        (50, 90),
        (90, 50),
        # (90, 90),
        # (90, 90),
    ]
    probability_left = 0.9  # fixme: hardcoded
    probability_right = 0.1  # fixme: hardcoded

    sound_delay_correction = 0

    trial_data = []

    def __init__(self, bpod=None, save_path_data=None):
        super(TaskControl, self).__init__()

        if not bpod:
            raise ValueError("required input argument: bpod")
        self.bpod = bpod

        self.save_path_data = (
            get_session_file_basename(bpod) if not save_path_data else save_path_data
        )

        self.sound = Sounds()

        self.sound_delay_correction = get_sound_delay_correction_value()
        self.valve_times_dict = get_calibration_point_for_valve(
            valves=task_settings.HARDWARE_VALVES_FOR_WATER,
            target_volume=task_settings.REWARD_AMOUNT_UL,
        )

        # copy task_settings to session folder
        src = Path(task_settings.__file__)
        dst = self.save_path_data.parent / src.name
        shutil.copy(src=str(src), dst=str(dst))

        logging.debug("Task control class created.")

    def softcode_handler(self, softcode=None):
        self.sound.soft_code_handler_function(softcode=softcode)

    def update(self, trial_data=None):
        logging.debug("Updating after trial.", trial_data)

    def reset_block(self):
        logging.debug("Resetting block.")
        pass  # switch to new block / reset relevant variables

    def draw_next_trial(self):
        if self.criterion_block_switch_reached or self.trial_number < 1:
            self.reset_block()

        # TODO: write basic SMA for PS task, including block update rules fixed trials vs criterion
        # TODO: write online plotting functions
        # TODO: write analysis module to save data preprocessed

        # make SMA
        sma = self.make_state_machine()
        logging.debug("New trial drawn")
        return sma

    def make_state_machine(self):
        logging.debug("Making new StateMachine.")
        # side probabilities ?
        current_choice_outcome_left = 1 if withprob(self.probability_left) else 0
        current_choice_outcome_right = 1 if withprob(self.probability_right) else 0
        # is stop trial ?
        give_stop_signal = task_settings.USE_STOP_TRIALS and withprob(
            task_settings.STOP_TRIAL_PROPORTION
        )
        if give_stop_signal:
            # if stop, also punish ?
            current_choice_outcome_left = (
                -1
                if task_settings.PUNISH_STOP_TRIALS
                and withprob(task_settings.PUNISH_STOP_TRIALS_PROPORTION)
                else 0
            )
            current_choice_outcome_right = (
                -1
                if task_settings.PUNISH_STOP_TRIALS
                and withprob(task_settings.PUNISH_STOP_TRIALS_PROPORTION)
                else 0
            )

        # LIGHTS - if intensity - for chosen ports (center/side)
        output_actions__center_ready = []
        output_actions__center_delay = []
        output_actions__side_ready = []
        if task_settings.HARDWARE_PORT_LIGHT_INTENSITY:
            if "center" in task_settings.HARDWARE_PORT_LIGHT_PORTS:
                output_actions__center_ready = [
                    (
                        Bpod.OutputChannels.PWM2,
                        task_settings.HARDWARE_PORT_LIGHT_INTENSITY,
                    )
                ]
                output_actions__center_delay = output_actions__center_ready
            if "side" in task_settings.HARDWARE_PORT_LIGHT_PORTS:
                output_actions__side_ready = [
                    (
                        Bpod.OutputChannels.PWM1,
                        task_settings.HARDWARE_PORT_LIGHT_INTENSITY,
                    ),
                    (
                        Bpod.OutputChannels.PWM3,
                        task_settings.HARDWARE_PORT_LIGHT_INTENSITY,
                    ),
                ]

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
            state_timer=30,
            state_change_conditions={Bpod.Events.Port2In: "center_initiating"},
            output_actions=output_actions__center_ready,
        )
        # INIT long enough -> proceed. pulled out too early -> back to center_ready
        sma.add_state(
            state_name="center_initiating",
            state_timer=task_settings.DELAY_UNTIL_CENTER_INIT,
            state_change_conditions={
                Bpod.Events.Port2Out: "center_ready",  # ABORTED
                Bpod.Events.Tup: "side_ready",
            },  # CONTINUE
            output_actions=output_actions__center_delay,
        )
        # TRAVEL to side -> wait for entry
        if give_stop_signal:
            # TODO:  give stop signal sound -> contingency will be no reward for the ports
            # TODO: add state before side_ready to drop soft_code for sound
            sma.add_state(
                state_name="side_ready",
                state_timer=task_settings.DELAY_UNTIL_SIDE_TIMEOUT_FOR_STOPPING,
                state_change_conditions={
                    Bpod.Events.Port1In: "choice_left",
                    Bpod.Events.Port3In: "choice_right",
                    Bpod.Events.Tup: "exit",
                },
                output_actions=output_actions__side_ready,
            )
        else:
            sma.add_state(
                state_name="side_ready",
                state_timer=task_settings.DELAY_UNTIL_SIDE_TIMEOUT,
                state_change_conditions={
                    Bpod.Events.Port1In: "choice_left",
                    Bpod.Events.Port3In: "choice_right",
                    Bpod.Events.Tup: "exit",
                },
                output_actions=output_actions__side_ready,
            )

        # Outcomes: LEFT  --  Encoding:  0=unrewarded, 1=rewarded, -1=punish with air
        if current_choice_outcome_left > 0:  # REWARD
            left_valve = task_settings.HARDWARE_VALVES_FOR_WATER[0]
            output_action_left_valve = [(Bpod.OutputChannels.Valve, left_valve)]
            valve_left_outcome = self.valve_times_dict[left_valve]
        elif current_choice_outcome_left < 0:  # PUNISH
            output_action_left_valve = [
                (Bpod.OutputChannels.Valve, task_settings.HARDWARE_VALVES_FOR_AIR[0])
            ]
            valve_left_outcome = task_settings.PUNISH_AIR_DURATION_MS
        else:  # == 0
            output_action_left_valve = []
            valve_left_outcome = 0

        # Outcomes: RIGHT  --  Encoding:  0=unrewarded, 1=rewarded, -1=punish with air
        if current_choice_outcome_right > 0:  # REWARD
            right_valve = task_settings.HARDWARE_VALVES_FOR_WATER[1]
            output_action_right_valve = [(Bpod.OutputChannels.Valve, right_valve)]
            valve_right_outcome = self.valve_times_dict[right_valve]
        elif current_choice_outcome_right < 0:  # PUNISH
            output_action_right_valve = [
                (Bpod.OutputChannels.Valve, task_settings.HARDWARE_VALVES_FOR_AIR[1])
            ]
            valve_right_outcome = task_settings.PUNISH_AIR_DURATION_MS
        else:  # == 0
            output_action_right_valve = []
            valve_right_outcome = 0

        sma.add_state(
            state_name="choice_left",
            state_timer=valve_left_outcome,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=output_action_left_valve + [],
        )
        sma.add_state(
            state_name="choice_right",
            state_timer=valve_right_outcome,
            state_change_conditions={Bpod.Events.Tup: "final"},
            output_actions=output_action_right_valve + [],
        )
        # Cleanup
        sma.add_state(
            state_name="final",
            state_timer=task_settings.STATE_DURATION_FINAL,
            state_change_conditions={
                Bpod.Events.Port1Out: "exit",
                Bpod.Events.Port2Out: "exit",
                Bpod.Events.Port3Out: "exit",
                Bpod.Events.Tup: "exit",
            },
            output_actions=[],
        )
        # END
        return sma

    def save(self):
        logging.debug("Saving task control data.")
        df = pd.DataFrame(self.trial_data)
        df.to_csv(self.save_path_data)


# class TaskData(object):
#     data = []
#     save_path = None
#
#     def __init__(self, save_path=None):
#         super(TaskData, self).__init__()
#
#         if not save_path:
#             raise ValueError("required input argument: save_path")
#
#         self.save_path = str(save_path)
#
#     def append(self, trial_data):
#         self.data.append(
#             trial_data
#         )  # TODO: make list for output data, then save as csv
#
#     def save(self):
#         data = pd.DataFrame(data=self.data)
#         data.to_csv(self.save_path)
#
#
# class OnlinePlotting(object):
#     save_path = None
#     save_fig_ext = ".eps"
#     save_fig_param = {"dpi": 400}
#
#     figure = None
#     axes = None
#
#     def __init__(self, save_path=None):
#         super(OnlinePlotting, self).__init__()
#
#         self.save_path = os.path.splitext(save_path)[0]
#
#         self.figure = pg.plot(title="TEST pg")
#         self.figure.plot([1], [1], pen=None)
#         # self.axes = plot.subplots(ncols=1, nrows=2)
#
#     def update(self, task_data=None):
#         # FIXME: implement plots
#         x = np.random.normal(size=1000)
#         y = np.random.normal(size=1000)
#         self.figure.plot(x, y, pen=None, symbol="o")
#         self.figure.show()
#         # self.axes[0].plot(np.random.random(), np.random.random(), "k+")
#         # self.axes[0].format(xlim=(0, 1), ylim=(0, 1))
#         # self.figure.canvas.draw_idle()  # slow: takes .5 sec
#         # plt.pause(0.001)
#
#     def save(self):
#         pass
#         # self.figure.savefig(self.save_path + self.save_fig_ext, **self.save_fig_param)
#
#     def bpod_loop_handler(self):
#         pass
#         # self.figure.canvas.flush_events()
