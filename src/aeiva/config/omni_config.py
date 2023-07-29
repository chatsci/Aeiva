#!/usr/bin/env python
# coding=utf-8
"""
This module contains the omniconfig classes.

We can define separate config classes for different modules, e.g., data, model, trainer, etc.
The OmniConfig class is the combination of all config classes.
It can also accept command line arguments to update the config values.

Copyright (C) 2023 Bang Liu - All Rights Reserved.
This source code is licensed under the license found in the LICENSE file
in the root directory of this source tree.
"""
from dataclasses import dataclass
import argparse
from typing import Union
from aeiva.config.base_config import BaseConfig


@dataclass
class OmniConfig(BaseConfig):
    @staticmethod
    def create_omni_config():
        defaults = {}
        for config_class_name, config_class in BaseConfig.subclasses.items():
            if config_class_name == "OmniConfig":
                continue
            for field, field_type in config_class.__annotations__.items():
                if field in defaults:
                    raise ValueError(f"Overlapping config argument: '{field}' found in {config_class.__name__}")
                default_value = getattr(config_class(), field, None)
                defaults[field] = default_value
        def __init__(self, **kwargs):
            for key, default_value in defaults.items():
                setattr(self, key, kwargs.get(key, default_value))
        OmniConfig.__init__ = __init__
        return OmniConfig

    def update_from_args(self, namespace_args: argparse.Namespace):
        for key, value in vars(namespace_args).items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)

    def get_argparse_parser(self):
        parser = argparse.ArgumentParser()
        for config_class_name, config_class in BaseConfig.subclasses.items():
            if config_class_name == "OmniConfig":
                continue
            for field, field_obj in config_class.__dataclass_fields__.items():
                field_type = field_obj.type
                # Check if the field is Optional
                if getattr(field_type, "__origin__", None) is Union:
                    field_type = field_type.__args__[0]
                if field_type is int:
                    parser.add_argument('--' + field, type=int, help=field_obj.metadata.get("help", f"{field} (int)"))
                elif field_type is float:
                    parser.add_argument('--' + field, type=float, help=field_obj.metadata.get("help", f"{field} (float)"))
                elif field_type is str:
                    parser.add_argument('--' + field, type=str, help=field_obj.metadata.get("help", f"{field} (str)"))
                elif field_type is bool:
                    parser.add_argument('--' + field, action='store_true', help=field_obj.metadata.get("help", f"{field} (bool)"))
                else:
                    print(f"Warning: unsupported type {field_type} for field '{field}'")
        return parser
