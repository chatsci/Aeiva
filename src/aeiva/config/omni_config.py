# omni_config.py

#!/usr/bin/env python
# coding=utf-8
"""
This module contains the OmniConfig classes.

We can define separate config classes for different modules, e.g., data, model, trainer, etc.
The OmniConfig class is the combination of all config classes.
It can also accept command line arguments to update the config values.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""

from dataclasses import dataclass, field
import argparse
from typing import Union, List, Tuple, Dict, Any, get_origin, get_args
import json
import enum

from aeiva.config.base_config import BaseConfig

@dataclass
class OmniConfig(BaseConfig):
    @staticmethod
    def create_omni_config():
        """
        Initializes OmniConfig by aggregating all configuration classes.
        """
        # Aggregating default values from all config classes
        defaults = {}
        for config_class_name, config_class in BaseConfig.subclasses.items():
            if config_class_name == "OmniConfig":
                continue
            for field_name, field_obj in config_class.__dataclass_fields__.items():
                if field_name in defaults:
                    raise ValueError(f"Overlapping config argument: '{field_name}' found in {config_class.__name__}")
                default_value = getattr(config_class(), field_name, None)
                defaults[field_name] = default_value

        def __init__(self, **kwargs):
            for key, default_value in defaults.items():
                setattr(self, key, kwargs.get(key, default_value))

        OmniConfig.__init__ = __init__
        return OmniConfig

    def update_from_args(self, namespace_args: argparse.Namespace):
        """
        Updates the configuration based on parsed command-line arguments.
        """
        for key, value in vars(namespace_args).items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)

    def get_argparse_parser(self):
        """
        Creates an argument parser that can handle complex types.
        """
        parser = argparse.ArgumentParser()
        for config_class_name, config_class in BaseConfig.subclasses.items():
            if config_class_name == "OmniConfig":
                continue
            for field_name, field_obj in config_class.__dataclass_fields__.items():
                field_type = field_obj.type

                # Handle Optional types
                if get_origin(field_type) is Union and type(None) in get_args(field_type):
                    field_type = next(arg for arg in get_args(field_type) if arg is not type(None))

                arg_name = '--' + field_name
                help_msg = field_obj.metadata.get("help", f"{field_name} ({field_type})")

                origin = get_origin(field_type)
                args = get_args(field_type)

                # Handle Enums
                if isinstance(field_type, type) and issubclass(field_type, enum.Enum):
                    choices = [item.value for item in field_type]
                    parser.add_argument(arg_name, type=str, choices=choices, help=help_msg)
                    continue

                # Handle list types
                if origin is list:
                    item_type = args[0]
                    if item_type is str:
                        parser.add_argument(arg_name, nargs='+', type=str, help=help_msg)
                    elif item_type is int:
                        parser.add_argument(arg_name, nargs='+', type=int, help=help_msg)
                    else:
                        # Default to strings if item type is not specifically handled
                        parser.add_argument(arg_name, nargs='+', type=str, help=help_msg)
                    continue

                # Handle tuple types
                if origin is tuple:
                    # Accept comma-separated values and convert to tuple
                    def tuple_type(s):
                        try:
                            return tuple(map(int, s.split(',')))
                        except ValueError:
                            raise argparse.ArgumentTypeError("Tuples must be comma-separated integers.")

                    parser.add_argument(arg_name, type=tuple_type, help=help_msg)
                    continue

                # Handle dict types
                if origin is dict:
                    # Expect JSON string
                    def dict_type(s):
                        try:
                            return json.loads(s)
                        except json.JSONDecodeError:
                            raise argparse.ArgumentTypeError("Dictionaries must be valid JSON strings.")

                    parser.add_argument(arg_name, type=dict_type, help=help_msg)
                    continue

                # Handle basic types
                if field_type is int:
                    parser.add_argument(arg_name, type=int, help=help_msg)
                elif field_type is float:
                    parser.add_argument(arg_name, type=float, help=help_msg)
                elif field_type is str:
                    parser.add_argument(arg_name, type=str, help=help_msg)
                elif field_type is bool:
                    parser.add_argument(arg_name, action='store_true', help=help_msg)
                else:
                    print(f"Warning: unsupported type {field_type} for field '{field_name}'")
        return parser