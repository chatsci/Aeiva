#!/usr/bin/env python
# coding=utf-8
""" This module contains the base class for all environment classes.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC


class BaseEnv(ABC):
    """ This class is the base class for all environment classes.
    """

    def __init__(self, *args, **kwargs):
        self.state = None
    
    def reset(self, *args, **kwargs):
        """ Reset the environment.
        """
        pass

    def step(self, action, *args, **kwargs):
        """ Take a step in the environment, and return the next state, reward, and done.
        """
        pass

