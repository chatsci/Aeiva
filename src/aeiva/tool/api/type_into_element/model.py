# tools/type_into_element/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class TypeIntoElementErrorCode:
    MISSING_POSITION_KEY = "MISSING_POSITION_KEY"
    POSITION_OUT_OF_BOUNDS = "POSITION_OUT_OF_BOUNDS"
    TYPE_INTO_ELEMENT_FAILED = "TYPE_INTO_ELEMENT_FAILED"
    SUCCESS = "SUCCESS"

class TypeIntoElementParams(BaseModel):
    position: Dict[str, float] = Field(..., description="The position dictionary containing 'x', 'y', 'width', 'height'.")
    text: str = Field(..., description="The text to type into the input field.")

class TypeIntoElementResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")