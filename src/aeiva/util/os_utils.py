import getpass
from typing import Optional

def get_os_user() -> str:
    """
    Retrieve the current OS username.

    Returns:
        str: The current OS user's name.
    """
    return getpass.getuser()