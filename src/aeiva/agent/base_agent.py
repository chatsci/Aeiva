#!/usr/bin/env python
# coding=utf-8
""" This module contains the base class for all agent classes.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from abc import ABC


class BaseAgent(ABC):
    """ This class is the base class for all agent classes.
    """
    
    def __init__(self, *args, **kwargs):
        self.backend = None
        self.frontend = None
        self.sensor = None
        self.actor = None
        self.world_model = None
        self.memory = None
        self.env = None
        self.state = None
        self.critic = None
        self.reward = None
        self.tools = None
        self.done = None

    def reset(self, *args, **kwargs):
        """ Reset the agent.
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

    def learn(self, *args, **kwargs):
        """ Learn from the environment.
        """
        pass

    def plan(self, *args, **kwargs):
        """ Plan in the environment.
        """
        pass

    def update(self, *args, **kwargs):
        """ Update the agent.
        """
        pass

    def save(self, *args, **kwargs):
        """ Save the agent.
        """
        pass

    def load(self, *args, **kwargs):
        """ Load the agent.
        """
        pass

    def close(self, *args, **kwargs):
        """ Close the agent.
        """
        pass

    def __del__(self):
        self.close()        
