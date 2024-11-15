from enum import Enum
from pydantic import BaseModel, Field


class CalculatorParams(BaseModel):
    operation: str = Field(
        ...,
        description="A mathematical expression, e.g., `200*7` or `5000/2*10`.",
    )


class CalculatorResult(BaseModel):
    output: t.Optional[str] = Field(
        None,
        description="Result of the calculation.",
    )
    error: t.Optional[str] = Field(
        None,
        description="Error message, if any.",
    )
    error_code: t.Optional[str] = Field(
        None,
        description="Error code representing the result state.",
    )


class CalculatorErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    INVALID_OPERATION = "INVALID_OPERATION"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"