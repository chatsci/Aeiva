"""
TODO:
    - add support for sampling with replacement
    - make draw_samples work for any iterable (not just lists)
    - write tests
"""
import numpy as np


def draw_samples(input_list, sample_ratio_or_num_samples):
    """ Draw samples from a list.
    """
    num_samples = sample_ratio_or_num_samples if sample_ratio_or_num_samples > 1 else int(sample_ratio_or_num_samples * len(input_list))

    if num_samples > len(input_list):
        sampled_indices = np.random.choice(len(input_list), num_samples, replace=True)
    else:
        sampled_indices = np.random.choice(len(input_list), num_samples, replace=False)

    sampled_input = [input_list[i] for i in sampled_indices]

    return sampled_input