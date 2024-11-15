# common/config.py

from dataclasses import dataclass, field
from typing import List, Dict
from aeiva.config.base_config import BaseConfig

@dataclass
class ToolkitConfig(BaseConfig):
    """
    Configuration for the Toolkit.
    """

    allowed_directories: List[str] = field(
        default_factory=lambda: ["/tmp/", "/home/user/allowed_directory/"],
        metadata={"help": "Directories that tools are allowed to access."}
    )
    # Mapping from OS usernames to roles
    user_role_mapping: Dict[str, str] = field(
        default_factory=lambda: {
            "admin_user": "admin",
            "regular_user": "user"
            # Add more user-role mappings as needed
        },
        metadata={"help": "Mapping of OS usernames to their roles."}
    )
    # Define permissions for each role
    role_permissions: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "admin": ["delete_file", "view_file", "create_file"],
            "user": ["view_file", "create_file"]
        },
        metadata={"help": "Mapping of roles to allowed API functions."}
    )
    # Add more configuration fields as needed