import logging
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from pybpodapi.protocol import Bpod
from pybpodapi.protocol import StateMachine

from pybpod_tools.tasks.probabilistic_switching import task_settings
from pybpod_tools.tools.calibration_handling import get_calibration_point_for_valve
from pybpod_tools.tools.calibration_handling import get_sound_delay_correction_value
from pybpod_tools.tools.maths import ExponentialMovingAverage
from pybpod_tools.tools.maths import withprob
from pybpod_tools.tools.misc import get_session_file_basename
from pybpod_tools.tools.sounds import Sounds
from pybpod_tools.tools.specific_state_machines import add_trial_onset_ttl


class TaskControl(object):
    bpod = None
    sound = None
    sound_delay_correction = 0

    trial_data = []
    save_path_data = None

    # Task progress
    trial_index = 0
    block_number = 0
    block_trial_number = 0
    reward_number = 0

    # Block switches -- length range: 25 - 45
    min_block_length = 15
    mean_neutral_block_length = 25
    min_trials_post_criterion = 10
    trials_post_criterion = 0

    criterion_contrast_blocks = 0.8
    criterion_neutral_blocks = 0.6
    criterion_tau = 8
    criterion_block_switch_reached = False
    block_switch_hazard_rate = 1 / (mean_neutral_block_length - min_block_length)

    moving_average = ExponentialMovingAverage(tau=criterion_tau, init_value=0.5)

    probabilities = task_settings.PROBABILITIES
    block_probability_index = None
    probability_left = 0
    probability_right = 0

    next_trial_choice_outcome_left = 0
    next_trial_choice_outcome_right = 0
    next_trial_give_stop_signal = 0

    def __init__(self, bpod=None, save_path_data=None):
        super(TaskControl, self).__init__()

        if not bpod:
            raise ValueError("Required input argument: bpod")
        self.bpod = bpod

        self.save_path_data = (
            get_session_file_basename(bpod) if not save_path_data else save_path_data
        )

        # todo: implement loading of presets for basic PS (no stop)
        #  and stop signal PS (adaptive stops, probabilities all 1/0 for analysis simplicity)

        # fixme: use hardware params for go/stop signal generation
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

    def switch_block(self):
        logging.debug("Resetting block.")
        self.block_number += 1
        self.block_trial_number = 0
        self.trials_post_criterion = 0
        self.criterion_block_switch_reached = False
        self.moving_average.reset()

        # probabilities
        if not self.block_probability_index:
            self.block_probability_index = 0

        next_probs_allowed = set(np.arange(len(self.probabilities))) - {
            self.block_probability_index
        }
        self.block_probability_index = random.randint(0, len(next_probs_allowed))
        self.probability_left, self.probability_right = (
            next_probs_allowed[self.block_probability_index] / 100
        )  # fixme: convert to probability

        print(
            f"New block #{self.block_number} after trial #{self.trial_index} with probabilities {next_probs_allowed[self.block_probability_index]}"
        )

        # TODO: block update rules fixed trials vs criterion

    def update(self, trial_index=None, trial_data=None):
        if trial_index < 1:
            self.switch_block()

        last_choice = -1  # TODO: GET
        rewarded = 1  # TODO: GET

        print(f"Updating after trial #{trial_index}")
        # trial_data is: bpod start ts, trial start ts, trial end ts, state and event ts
        self.trial_index = trial_index
        self.block_trial_number += 1
        self.trial_data.append(trial_data)

        # Update last choice
        self.moving_average.update(latest_sample=last_choice)
        # Update last outcome: reward/neutral/punish
        if rewarded:
            self.reward_number += 1

        # Check for block criterion
        neutral_block_bias = (
            (1 - self.criterion_neutral_blocks)
            <= self.moving_average
            <= self.criterion_neutral_blocks
        )

        if self.criterion_block_switch_reached:
            self.trials_post_criterion += 1
        elif (
            (self.probability_left == self.probability_right and neutral_block_bias)
            or (
                self.probability_left > self.probability_right
                and self.moving_average > self.criterion_contrast_blocks
            )
            or (
                self.probability_right > self.probability_left
                and self.moving_average < self.criterion_contrast_blocks
            )
        ):
            self.criterion_block_switch_reached = True

        # # Check for block switch (trial based)
        if self.block_trial_number >= self.min_block_length and (
            self.probability_left == self.probability_right
            and withprob(self.block_switch_hazard_rate)
            or self.trials_post_criterion >= self.min_trials_post_criterion
        ):
            self.switch_block()

        # TODO: write online plotting functions: self.redraw_figure()

    def draw_next_trial(self):
        # side probabilities ?
        self.next_trial_choice_outcome_left = (
            1 if withprob(self.probability_left) else 0
        )
        self.next_trial_choice_outcome_right = (
            1 if withprob(self.probability_right) else 0
        )
        # is stop trial ?
        self.next_trial_give_stop_signal = task_settings.USE_STOP_TRIALS and withprob(
            task_settings.STOP_TRIAL_PROPORTION
        )
        if self.next_trial_give_stop_signal:
            # if stop, also punish ?
            self.next_trial_choice_outcome_left = (
                -1
                if task_settings.PUNISH_STOP_TRIALS
                and withprob(task_settings.PUNISH_STOP_TRIALS_PROPORTION)
                else 0
            )
            self.next_trial_choice_outcome_right = (
                -1
                if task_settings.PUNISH_STOP_TRIALS
                and withprob(task_settings.PUNISH_STOP_TRIALS_PROPORTION)
                else 0
            )

        # TODO: STOP signal adaptive testing here: change of stop signal delay ++ self.sound_delay_correction

        # Stimulation
        if task_settings.STIMULATION and withprob(
            task_settings.STIMULATION_TRIAL_PROPORTION
        ):
            pass
            # TODO: implement STIMULATION trials:
            #  connect pulsepal, upload stim settings, add BNC event to output actions

        # make SMA
        sma = self.make_state_machine()
        logging.debug("New trial drawn")
        return sma

    def make_state_machine(self):
        logging.debug("Making new StateMachine.")

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
        if self.next_trial_give_stop_signal:
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
        # note: stop signal outcomes set to 0 in next-trial
        if self.next_trial_choice_outcome_left > 0:  # REWARD
            left_valve = task_settings.HARDWARE_VALVES_FOR_WATER[0]
            output_action_left_valve = [(Bpod.OutputChannels.Valve, left_valve)]
            valve_left_outcome = self.valve_times_dict[left_valve]
        elif self.next_trial_choice_outcome_left < 0:  # PUNISH
            output_action_left_valve = [
                (Bpod.OutputChannels.Valve, task_settings.HARDWARE_VALVES_FOR_AIR[0])
            ]
            valve_left_outcome = task_settings.PUNISH_AIR_DURATION_MS
        else:  # == 0
            output_action_left_valve = []
            valve_left_outcome = 0

        # Outcomes: RIGHT  --  Encoding:  0=unrewarded, 1=rewarded, -1=punish with air
        if self.next_trial_choice_outcome_right > 0:  # REWARD
            right_valve = task_settings.HARDWARE_VALVES_FOR_WATER[1]
            output_action_right_valve = [(Bpod.OutputChannels.Valve, right_valve)]
            valve_right_outcome = self.valve_times_dict[right_valve]
        elif self.next_trial_choice_outcome_right < 0:  # PUNISH
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
        # TODO: write analysis module to save data preprocessed
        df = pd.DataFrame(self.trial_data)
        df.to_csv(self.save_path_data)
