from typing import Any, Dict, List, Type, Union, Optional, Tuple
import yaml

from aeiva.util.json_utils import load_json, dump_json


class Profile:
    """
    Class for the profile of an agent in a society.
    """
    def __init__(self, profile_path: str):
        self.profile_path = profile_path
        self.profile_content = {}
        self.load_profile(profile_path)

    def load_profile(self, path: str) -> None:
        self.content = load_json(path)

    def save_profile(self, path: str) -> None:
        dump_json(self.content, path)
    
    def to_string(self) -> str:
        # print the content of the profile in yaml format
        yaml_string=yaml.dump(self.profile_content)
        return yaml_string
