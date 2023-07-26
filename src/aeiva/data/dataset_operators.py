#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains the utils for processing datasets.

A dataset in aeiva is a dictionary with the following structure:
{
    "data": [
        {sample1}, {sample2}, ..., {sampleN}
    ],
    "metadata": {
        "num_samples": XX, 
        ...
    }
}
where each sample is a dictionary itself, and metadata is a dictionary that contains the number of samples
and possibly other fields.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-13

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
import random
import pickle
from aeiva.util.file_utils import ensure_dir


def merge_datasets(datasets):
    """
    Merge multiple datasets into one.
    """
    merged_data = []
    total_samples = 0
    for dataset in datasets:
        merged_data.extend(dataset["data"])
        total_samples += dataset["metadata"]["num_samples"]

    return {"data": merged_data, "metadata": {"num_samples": total_samples}}


def sample_from_dataset(dataset, n_samples):
    """
    Sample a number of samples from a dataset.
    """
    random_indices = random.sample(range(dataset["metadata"]["num_samples"]), n_samples)
    sampled_data = [dataset["data"][i] for i in random_indices]
    return {"data": sampled_data, "metadata": {"num_samples": n_samples}}


def preserve_keys_in_dataset(dataset, keys_to_preserve):
    """
    Filter the dataset to only include specified keys in each sample.
    """
    filtered_data = []
    for sample in dataset["data"]:
        for key in keys_to_preserve:
            if key not in sample:
                raise KeyError(f"Key {key} not found in sample")
        filtered_sample = {key: sample[key] for key in keys_to_preserve if key in sample}
        filtered_data.append(filtered_sample)
    return {"data": filtered_data, "metadata": dataset["metadata"]}


def save_dataset(dataset, output_path):
    """Save a dataset to a file by pickling it."""
    ensure_dir(output_path)
    pickle.dump(dataset, open(output_path, "wb"), protocol=4)
