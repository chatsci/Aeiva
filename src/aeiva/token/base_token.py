# coding=utf-8
#
# Copyright (C) 2023 Bang Liu - All Rights Reserved.
# This source code is licensed under the license found in the LICENSE file
# in the root directory of this source tree.
""" 
This module contains the base class for all token classes.
"""
from abc import ABC, abstractmethod

# constants
MODALITY2ID = {
    'text': 0,
    'image': 1,
    'audio': 2,
    'video': 3,
    'document': 4,
    'table': 5,
    'chart': 6,
    'math': 7,
    'code': 8,
    'other': 9
}
MASK2ID = {
    'pad': 0,
    'token': 1
}
TYPE2ID = {
    'sos': 0,
    'eos': 1,
    'pad': 2,
    'token': 3,
    'cls': 4,
    'sep': 5,
    'mask': 6,
    'unk': 7,
    'other': 8
}


class BaseToken(ABC):
    """ This class is the base class for all token classes.
    """
    pass


class Token(BaseToken):
    """ This class represents a multimodal token, e.g., text, image, audio, or video token.
    """
    def __init__(self, *args, **kwargs):
        """ Initialize a text token.
        """
        # common
        self.raw_data = kwargs.get('raw_data', None)
        self.embeddings = kwargs.get('embeddings', None)
        self.token_id = kwargs.get('token_id', None)
        self.type_id = kwargs.get('type_id', None)
        self.modality_id = kwargs.get('modality_id', None)
        self.pos = kwargs.get('pos', None)
        self.mask_id = kwargs.get('mask_id', None)

        # image
        self.size = kwargs.get('size', None)
        self.num_channels = kwargs.get('num_channels', None)

        # audio
        self.sampling_rate = kwargs.get('sampling_rate', None)

        # video
        self.timestamp = kwargs.get('timestamp', None)
        self.duration = kwargs.get('duration', None)
    
    def __str__(self):
        return str(self.__dict__)
    
    def __repr__(self):
        return str(self.__dict__)
    
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
