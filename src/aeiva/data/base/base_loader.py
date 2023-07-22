# coding=utf-8
#
# Copyright (C) 2023 Bang Liu - All Rights Reserved.
# This source code is licensed under the license found in the LICENSE file
# in the root directory of this source tree.
""" 
This module contains the base class for all dataloader classes.
"""
from torch.utils.data import Dataset, DataLoader
from abc import ABC, abstractmethod
from typing import Any


class BaseDataset(Dataset, ABC):
    def __init__(self, processed_data: dict[str, Any], config: dict):
        super().__init__()
        self.processed_data = processed_data
        self.config = config

    @abstractmethod
    def __getitem__(self, index):
        """Get a sample by index."""
        pass

    def __len__(self):
        """Get the length of the dataset."""
        return len(self.processed_data)


class BaseDataLoader(DataLoader, ABC):
    @abstractmethod
    def __init__(self, dataset: BaseDataset, config: dict):
        pass
