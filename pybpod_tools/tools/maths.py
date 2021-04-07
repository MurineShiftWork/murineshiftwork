import random


def withprob(probability=None):
    return random.random() < probability
