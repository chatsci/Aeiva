# toolkit/shell_toolkit/create_new_shell_session/model.py

from enum import Enum
from pydantic import BaseModel, Field

class CreateNewShellSessionParams(BaseModel):
    session_name: str = Field(
        None,
        description="A custom name for the shell session. If not provided, a unique ID will be used."
    )
    shell_type: str = Field(
        None,
        description="The type of shell to use (e.g., 'bash', 'zsh', 'powershell', 'cmd'). Defaults to the system's default shell."
    )

class CreateNewShellSessionResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Details of the created shell session, including 'session_id' and 'session_name'."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class CreateNewShellSessionErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNSUPPORTED_SHELL_TYPE = "UNSUPPORTED_SHELL_TYPE"
    SHELL_NOT_FOUND = "SHELL_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FAILED_TO_CREATE_SESSION = "FAILED_TO_CREATE_SESSION"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"