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
where each sample is a dictionary itself, and metadata is a dictionary
that contains the number of samples and possibly other fields.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-13

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
import sys
import random
import pickle
import numpy as np
from typing import Optional, Callable, Tuple

from aeiva.common.types import DataSet
from aeiva.data.processor import process_dataset
from aeiva.util.file_utils import ensure_dir
from aeiva.common.decorators import (
    OPERATORS, import_submodules,
    register_data_filter, register_data_sampler)


import_submodules('aeiva.data.formatters')


def build_dataset(dataset_name: str,
                  input_filepaths_dict: dict[str, str],
                  pipeline: list[Callable],
                  output_dir: Optional[str],
                  max_samples: Optional[int] = sys.maxsize) -> DataSet:
    r""" Build a dataset by formatting and processing it.
    """
    operator_type = 'data_formatter'
    format_func = OPERATORS[operator_type][dataset_name]
    formatted_dataset = format_func(input_filepaths_dict, output_dir, max_samples)
    processed_dataset = process_dataset(formatted_dataset, pipeline, output_dir, dataset_name)
    print(f"Completed processing dataset: {dataset_name} (output_dir: {output_dir})")
    return processed_dataset


def merge_datasets(datasets: list[DataSet]) -> DataSet:
    r""" Merge multiple datasets into one.
    """
    merged_data = []
    total_samples = 0
    for dataset in datasets:
        merged_data.extend(dataset["data"])
        total_samples += dataset["metadata"]["num_samples"]
    result = {"data": merged_data, "metadata": {"num_samples": total_samples}}
    return result


def build_and_merge_datasets(dataset_names: list[str],
                             input_filepaths_dict: dict[str, str],
                             pipeline: list[Callable],
                             output_dir: Optional[str],
                             max_samples: Optional[int] = sys.maxsize) -> DataSet:
    r""" Build multiple datasets by formatting and processing them.
    """
    merged_datasets = []
    for dataset_name in dataset_names:
        dataset = build_dataset(dataset_name, input_filepaths_dict, pipeline, output_dir, max_samples)
        merged_datasets.append(dataset)
    result = merge_datasets(merged_datasets)
    return result


def sample_dataset(dataset: DataSet, n_samples: int) -> DataSet:
    r""" Sample a number of samples from a dataset.
    """
    random_indices = random.sample(range(dataset["metadata"]["num_samples"]), n_samples)
    sampled_data = [dataset["data"][i] for i in random_indices]
    return {"data": sampled_data, "metadata": {"num_samples": n_samples}}


def filter_dataset(dataset: DataSet, filter_criteria: str, *args, **kwargs) -> DataSet:
    r""" Filter a dataset by a filter function.
    """
    operator_type = 'data_filter'
    filter_func = OPERATORS[operator_type][filter_criteria]
    filtered_data = filter_func(dataset, *args, **kwargs)
    return filtered_data


@register_data_filter("filter_dataset_by_keys")
def filter_dataset_by_keys(dataset: DataSet, keys_to_preserve: list[str]) -> DataSet:
    r""" Filter the dataset to only include specified keys in each sample.
    """
    filtered_data = []
    for sample in dataset["data"]:
        for key in keys_to_preserve:
            if key not in sample:
                raise KeyError(f"Key {key} not found in sample")
        filtered_sample = {key: sample[key] for key in keys_to_preserve if key in sample}
        filtered_data.append(filtered_sample)
    return {"data": filtered_data, "metadata": dataset["metadata"]}


def split_dataset(dataset: dict, train_ratio: float, seed: int = 42) -> Tuple[dict]:
    r""" Split a dataset into a training set and a validation set.
    """
    np.random.seed(seed)  # ensures the function is deterministic
    
    data = dataset["data"]
    metadata = dataset["metadata"]
    
    # Create a permutation of indices and shuffle the data.
    perm = np.random.permutation(len(data))
    shuffled_data = [data[i] for i in perm]
    
    # Calculate split index
    split_idx = int(train_ratio * len(shuffled_data))
    
    # Split the shuffled data
    train_data = shuffled_data[:split_idx]
    val_data = shuffled_data[split_idx:]

    # Create metadata for training and validation datasets
    train_metadata = metadata.copy()
    train_metadata["num_samples"] = len(train_data)
    val_metadata = metadata.copy()
    val_metadata["num_samples"] = len(val_data)
    
    # Create training and validation datasets
    train_dataset = {"data": train_data, "metadata": train_metadata}
    val_dataset = {"data": val_data, "metadata": val_metadata}

    return train_dataset, val_dataset


def save_dataset(dataset: DataSet, output_path: str) -> None:
    r""" Save a dataset to a file by pickling it.
    """
    ensure_dir(output_path)
    pickle.dump(dataset, open(output_path, "wb"), protocol=4)
