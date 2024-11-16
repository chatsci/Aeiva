# toolkit/system_toolkit/get_network_info/model.py

from enum import Enum
from pydantic import BaseModel, Field

class GetNetworkInfoParams(BaseModel):
    # No parameters needed for this API
    pass

class GetNetworkInfoResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Network information of the system."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class GetNetworkInfoErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"