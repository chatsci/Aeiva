#!/usr/bin/env python
# coding=utf-8
""" This module contains the base class for all config classes.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC


def BaseConfig(ABC):
    """ This class is the base class for all config classes.
    """
    
    def __init__(self, *args, **kwargs):
        pass
    
    def reset(self, *args, **kwargs):
        """ Reset the config.
        """
        pass

    def set(self, *args, **kwargs):
        """ Set the config.
        """
        pass

    def get(self, *args, **kwargs):
        """ Get the config.
        """
        pass
