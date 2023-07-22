#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains the base class for all data formatter classes.

A data formatter turns raw data into a format that can be used by a processor.
It is responsible for loading, formatting, and saving data.
How the input and output files are composed and organized makes up the data formatter's interface.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-08

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseDataFormatter(ABC):
    subclasses = {}
    formatter_name = None  # Use this name to register the formatter.

    def __init_subclass__(cls, **kwargs):
        """Automatically register subclasses."""
        super().__init_subclass__(**kwargs)
        BaseDataFormatter.subclasses[cls.formatter_name] = cls
    
    @abstractmethod
    def __init__(self, *args, **kwargs):
        """Initialize the formatter."""
        pass

    @staticmethod
    def create(formatter_name):
        """Create a formatter by name."""
        if formatter_name not in BaseDataFormatter.subclasses:
            raise ValueError(f'Bad formatter name {formatter_name}')
        return BaseDataFormatter.subclasses[formatter_name]

    @abstractmethod
    def format(self, input_filepaths_dict: dict[str, str], *args, **kwargs) -> dict[str, Any]:
        """Format the data into a format that can be used by a processor."""
        pass

    def __call__(self, input_filepaths_dict: dict[str, str], *args, **kwargs):
        """Call the formatter by instance."""
        return self.format(input_filepaths_dict, *args, **kwargs)

