# toolkit/file_toolkit/copy_file_or_folder/model.py

from enum import Enum
from pydantic import BaseModel, Field

class CopyFileOrFolderParams(BaseModel):
    source: str = Field(
        ..., 
        description="The path of the file or folder to copy."
    )
    destination: str = Field(
        ..., 
        description="The target path where the file or folder will be copied."
    )

class CopyFileOrFolderResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the copy operation was successful."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class CopyFileOrFolderErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    DESTINATION_EXISTS = "DESTINATION_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FAILED_TO_COPY = "FAILED_TO_COPY"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"