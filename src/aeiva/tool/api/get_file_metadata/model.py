# toolkit/file_toolkit/get_file_metadata/model.py

from enum import Enum
from pydantic import BaseModel, Field

class GetFileMetadataParams(BaseModel):
    path: str = Field(
        ..., 
        description="The path of the file or folder."
    )

class GetFileMetadataResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Metadata information of the specified file or folder."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class GetFileMetadataErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    FAILED_TO_GET_METADATA = "FAILED_TO_GET_METADATA"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"