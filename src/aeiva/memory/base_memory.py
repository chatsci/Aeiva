#!/usr/bin/env python
# coding=utf-8
""" This module contains the base class for all memory classes.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC


class BaseMemory(ABC):
    """ This class is the base class for all memory classes.
    """

    def __init__(self, *args, **kwargs):
        self.memory = None

    def reset(self, *args, **kwargs):
        """ Reset the memory.
        """
        pass

    def read(self, *args, **kwargs):
        """ Read from the memory.
        """
        pass

    def write(self, *args, **kwargs):
        """ Write to the memory.
        """
        pass
