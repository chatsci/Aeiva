#!/usr/bin/env python
# coding=utf-8
"""
This module contains the config for macaw model.

We can define separate config classes for different specific models/datasets/tasks.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from dataclasses import dataclass, field
from typing import Optional
from aeiva.config.base_config import BaseConfig


@dataclass
class MacawConfig(BaseConfig):
    """
    Define user-customized config here.
    """
    image_dir: Optional[str] = field(
        default=None,
        metadata={"help": "The directory of image data"}
    )
    video_dir: Optional[str] = field(
        default=None,
        metadata={"help": "The directory of video data"}
    )
    frame_dir: Optional[str] = field(
        default=None,
        metadata={"help": "The directory to save video frames"}
    )
    audio_dir: Optional[str] = field(
        default=None,
        metadata={"help": "The directory to save video audios"}
    )
    num_frames_to_sample: Optional[int] = field(
        default=120,
        metadata={"help": "The number of frames to sample from a video"}
    )
    num_frames_to_load: Optional[int] = field(
        default=6,
        metadata={"help": "The number of frames to load as a part of model inputs"}
    )
    num_samples_per_dataset: Optional[int] = field(
        default=100,
        metadata={"help": "The number of samples to load from each dataset"}
    )
    num_samples_per_merged_dataset: Optional[int] = field(
        default=20,
        metadata={"help": "The number of samples to save after merging datasets"}
    )
    batch_size: Optional[int] = field(
        default=1,
        metadata={"help": "The batch size of model inputs"}
    )
    max_seq_len_for_preprocess: Optional[int] = field(
        default=256,
        metadata={"help": "The maximum sequence length for preprocess"}
    )
    run_time_cache_dir: Optional[str] = field(
        default=None,
        metadata={"help": "The directory to save running time data, such as video frames, audios, and so on."}
    )
    tokenizer_name_or_path: Optional[str] = field(
        default=None,
        metadata={"help": "The name or path of tokenizer"}
    )
    clip_model_name_or_path: Optional[str] = field(
        default=None,
        metadata={"help": "The name or path of clip model"}
    )
    whisper_model_name_or_path: Optional[str] = field(
        default=None,
        metadata={"help": "The name or path of whisper model"}
    )
    llama7b_model_name_or_path: Optional[str] = field(
        default=None,
        metadata={"help": "The name or path of llama7b model"}
    )
    macaw_model_name_or_path: Optional[str] = field(
        default=None,
        metadata={"help": "The name or path of macaw model"}
    )
    mode: Optional[str] = field(
        default="train",
        metadata={"help": "The mode of train, eval, or inference"}
    )
    model_name: Optional[str] = field(
        default="macaw",
        metadata={"help": "The name of model"}
    )
    resource_ready: Optional[bool] = field(
        default=True,
        metadata={"help": "Whether the pre-requisite resource is ready, e.g., download pretrained models and datasets"}
    )
