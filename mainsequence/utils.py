import random
import math


def weighted_random(choices):
    '''
    Pick a key at random from a dictionary where values are weights.`

    Args:
        choices: A dictionary mapping keys to real-numbered weights
        exp: If True, exponentiate all the weights. Note: If False, all
             weights must be positive.
        beta: Multiply all weights by this factor before exponentiating.
              When 0, makes all weights equal; large numbers make small
              weight differences increasingly likely.

    Returns:
        One of the keys, chosen at random.
    '''

    total = sum([v for v in choices.values()])
    target = random.random() * total
    counter = 0
    for k, v in choices.items():
        if counter + v >= target:
            return k
        counter += v
    else:
        raise Exception("Shouldn't be here")


def make_probabilities(choices, exp=True, beta=1.0):
    '''
    Convert a choice: weight dictionary into probabilities.

    Args:
        choices: A dictionary mapping keys to real-numbered weights
        exp: If True, exponentiate all the weights. Note: If False, all
             weights must be positive.
        beta: Multiply all weights by this factor before exponentiating.
              When 0, makes all weights equal; large numbers make small
              weight differences increasingly likely.

    Returns:
        A dictionary mapping keys to probabilities
    '''
    if exp:
        choices = {option: math.exp(beta * weight) 
                   for option, weight in choices.items()}

    total = sum([v for v in choices.values()])
    probabilities = {option: (weight / total) 
                     for option, weight in choices.items()}
    return probabilities