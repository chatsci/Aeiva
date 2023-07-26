#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains the classes for multi-modality data processor classes.

A data processor processes formatted data before training.
It turns formatted data into processed data.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-11

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from typing import Any, Callable
from aeiva.util.file_utils import ensure_dir
from aeiva.util.json_utils import dump_json
from aeiva.util.pipeline import Pipeline
from abc import ABC, abstractmethod


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
    def execute(self, formatted_data: dict[str, Any], *args, **kwargs) -> dict[str, Any]:
        """Preprocess the formatted data into processed data that can be used for training."""
        pass

    def __call__(self, formatted_data: dict[str, Any], *args, **kwargs):
        """Call the processor by instance."""
        return self.execute(formatted_data, *args, **kwargs)


class MultimodalProcessor(BaseProcessor):
    processor_name = "multimodal"

    def __init__(self, dataset_name: str, pipeline: list[Callable], output_dir: str, save_output: bool = True):
        self.dataset_name = dataset_name
        self.pipeline = Pipeline(pipeline)
        self.output_dir = output_dir
        self.save_output = save_output

    def execute(self, formatted_data: dict[str, Any]) -> dict[str, Any]:
        processed_data = []
        for item in formatted_data["data"]:
            processed_data.append(self.pipeline(item.copy()))
        
        output = {"data": processed_data, "metadata": formatted_data["metadata"]}
        if self.save_output:
            ensure_dir(self.output_dir)
            dump_json(output, f"{self.output_dir}/{self.dataset_name}_dataset.processed.json")
        return output
