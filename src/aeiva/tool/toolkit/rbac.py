# common/rbac.py

from typing import Dict, List
from aeiva.tool.toolkit.toolkit_config import ToolkitConfig

class PermissionError(Exception):
    """Custom exception for permission-related errors."""
    pass

def check_permission(user_role: str, api_name: str, config: ToolkitConfig) -> bool:
    """
    Check if the user_role has permission to execute the given api_name.

    Args:
        user_role (str): The role of the user.
        api_name (str): The name of the API function.
        config (ToolkitConfig): The toolkit configuration containing role permissions.

    Returns:
        bool: True if permitted, False otherwise.

    Raises:
        PermissionError: If the user does not have the required permission.
    """
    allowed_apis: List[str] = config.role_permissions.get(user_role, [])
    if api_name in allowed_apis:
        return True
    else:
        return False