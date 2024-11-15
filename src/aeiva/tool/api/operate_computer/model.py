from typing import Optional, Tuple
from pydantic import BaseModel


class OperateComputerParams(BaseModel):
    action: str
    text: Optional[str] = None
    coordinate: Optional[Tuple[int, int]] = None


class OperateComputerResult(BaseModel):
    output: Optional[str]
    base64_image: Optional[str]
    error: Optional[str]
    error_code: str


class OperateComputerErrorCode(str):
    SUCCESS = "SUCCESS"
    INVALID_ACTION = "INVALID_ACTION"
    INVALID_COORDINATE = "INVALID_COORDINATE"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    NOT_SUPPORTED = "NOT_SUPPORTED"