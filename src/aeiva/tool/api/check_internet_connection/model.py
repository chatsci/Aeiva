# toolkit/system_toolkit/check_internet_connection/model.py

from enum import Enum
from pydantic import BaseModel, Field

class CheckInternetConnectionParams(BaseModel):
    host: str = Field(
        "8.8.8.8",
        description="Host to connect to for checking internet connectivity."
    )
    port: int = Field(
        53,
        description="Port to connect to for checking internet connectivity."
    )
    timeout: float = Field(
        3.0,
        description="Connection timeout in seconds."
    )

class CheckInternetConnectionResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Connection status."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class CheckInternetConnectionErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_CHECK_CONNECTION = "FAILED_TO_CHECK_CONNECTION"