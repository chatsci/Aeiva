#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains the base class for multi-modality data processor classes.

A data processor processes formatted data before training.
It turns formatted data into processed data.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-11

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from typing import Any, Callable
from aeiva.data.base import BaseProcessor
from aeiva.util.file_utils import ensure_dir
from aeiva.util.json_utils import dump_json
from aeiva.util.pipeline import Pipeline


class MultimodalProcessor(BaseProcessor):
    processor_name = "multimodal"

    def __init__(self, dataset_name: str, pipeline: list[Callable], output_dir: str, save_output: bool = True):
        self.dataset_name = dataset_name
        self.pipeline = Pipeline(pipeline)
        self.output_dir = output_dir
        self.save_output = save_output

    def process(self, formatted_data: dict[str, Any]) -> dict[str, Any]:
        processed_data = []
        for item in formatted_data["data"]:
            processed_data.append(self.pipeline(item.copy()))
        
        output = {"data": processed_data, "metadata": formatted_data["metadata"]}
        if self.save_output:
            ensure_dir(self.output_dir)
            dump_json(output, f"{self.output_dir}/{self.dataset_name}_dataset.processed.json")
        return output
