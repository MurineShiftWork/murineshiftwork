import random

import numpy as np


def withprob(probability=None):
    return random.random() < probability


class ExponentialMovingAverage:
    avg = None

    def __init__(self, tau=None, init_value=0.0, function=None, decay_missing=True):
        if function:
            self.alpha = function(tau)
        else:
            self.alpha = 1 - np.exp(-1 / tau)
        self.inv_alpha = 1 - self.alpha
        self.init_value = init_value
        self.decay_missing = decay_missing
        self.reset()

    def __call__(self):
        return self.avg

    def reset(self, init_value=None):
        if init_value:
            self.init_value = init_value
        self.avg = self.init_value

    def update(self, latest_sample=None):
        """Average is weighted by decay of latest sample and all other decays(1-alpha) for previous samples.
        For missing values (nan), the current average decays
        """
        if np.isnan(latest_sample):
            if self.decay_missing:
                self.avg = self.avg * self.inv_alpha
            else:
                print(
                    f"{ExponentialMovingAverage}: Missing value and not allowed to decay anyhow."
                )
                return
        else:
            self.avg = (self.avg * self.inv_alpha) + (latest_sample * self.alpha)
