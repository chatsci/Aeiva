#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains the data processor.

@Author: Bang Liu (chatsci.ai@gmail.com)
@Date: 2023-07-11

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from typing import Callable, Optional

from aeiva.util.file_utils import ensure_dir
from aeiva.util.json_utils import dump_json
from aeiva.common.pipeline import Pipeline
from aeiva.common.types import DataSet, DataItem


def process_dataset(formatted_dataset: DataSet,
                    pipeline: list[Callable],
                    output_dir: Optional[str],
                    dataset_name: Optional[str] = "") -> DataSet:
    processed_data = []
    pipeline = Pipeline(pipeline)
    for item in formatted_dataset["data"]:
        processed_data.append(pipeline(item.copy()))
    
    output = {"data": processed_data, "metadata": formatted_dataset["metadata"]}
    if output_dir is not None:
        ensure_dir(output_dir)
        dump_json(output, f"{output_dir}/{dataset_name}_dataset.processed.json")
    return output
