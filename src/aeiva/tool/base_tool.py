#!/usr/bin/env python
# coding=utf-8
""" This module contains the base class for all tool classes.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC


class BaseTool(ABC):
    """ This class is the base class for all tool classes.
    """
    
    def __init__(self) -> None:
        super().__init__()
    
    def reset(self, *args, **kwargs):
        """ Reset the tool.
        """
        pass

    def act(self, *args, **kwargs):
        """ Act in the environment.
        """
        pass

    def sense(self, *args, **kwargs):
        """ Sense the environment.
        """
        pass
