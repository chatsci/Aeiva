# coding=utf-8
#
# Copyright (C) 2023 Bang Liu - All Rights Reserved.
# This source code is licensed under the license found in the LICENSE file
# in the root directory of this source tree.
"""
This module contains the base class for all tokenizer classes.
"""
from abc import ABC, abstractmethod
from typing import List


class BaseTokenizer(ABC):
    """
    Abstract base class for tokenizers.
    """

    @abstractmethod
    def encode(self, data: str, **kwargs) -> List[int]:
        pass

    @abstractmethod
    def decode(self, data: List[int], **kwargs) -> str:
        pass