# tools/test_operation/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class TestOperationErrorCode:
    TEST_OPERATION_FAILED = "TEST_OPERATION_FAILED"
    SUCCESS = "SUCCESS"

class TestOperationParams(BaseModel):
    a: int = Field(..., description="The first operand.")
    b: int = Field(..., description="The second operand.")

class TestOperationResult(BaseModel):
    output: Optional[int] = Field(None, description="The result of the test operation.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")