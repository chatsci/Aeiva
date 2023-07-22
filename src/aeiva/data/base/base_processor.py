#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains the base class for all data processor classes.

A data processor processes formatted data before training.
It turns formatted data into processed data.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-10

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC, abstractmethod
from typing import Any, Iterable


class BaseProcessor(ABC):
    subclasses = {}
    processor_name = None  # Use this name to register the processor.

    def __init_subclass__(cls, **kwargs):
        """Automatically register subclasses."""
        super().__init_subclass__(**kwargs)
        BaseProcessor.subclasses[cls.processor_name] = cls
    
    @abstractmethod
    def __init__(self, *args, **kwargs):
        """Initialize the processor."""
        pass

    @classmethod
    def create(cls, processor_name: str) -> Any:
        """Create a processor by name."""
        if processor_name not in BaseProcessor.subclasses:
            raise ValueError(f'Bad processor name {processor_name}')
        return BaseProcessor.subclasses[processor_name]

    @abstractmethod
    def process(self, formatted_data: dict[str, Any], *args, **kwargs) -> dict[str, Any]:
        """Preprocess the formatted data into processed data that can be used for training."""
        pass

    def __call__(self, formatted_data: dict[str, Any], *args, **kwargs):
        """Call the processor by instance."""
        return self.process(formatted_data, *args, **kwargs)
