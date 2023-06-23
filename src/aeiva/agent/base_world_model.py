#!/usr/bin/env python
# coding=utf-8
""" This module contains the base class for all world model classes.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC


def BaseWorldModel(ABC):
    """ This class is the base class for all world model classes.
    """
    
    def __init__(self, *args, **kwargs):
        self.world_model = None
    
    def reset(self, *args, **kwargs):
        """ Reset the world model.
        """
        pass

    def update(self, *args, **kwargs):
        """ Update the world model.
        """
        pass

    def predict(self, *args, **kwargs):
        """ Predict the world model.
        """
        pass

    def evaluate(self, *args, **kwargs):
        """ Evaluate the world model.
        """
        pass

    def learn(self, *args, **kwargs):
        """ Learn the world model.
        """
        pass
