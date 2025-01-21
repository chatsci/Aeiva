from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class InputTextOnWebpageErrorCode:
    SUCCESS = "SUCCESS"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    INPUT_TEXT_FAILED = "INPUT_TEXT_FAILED"

class InputTextOnWebpageParams(BaseModel):
    page_id: int = Field(..., description="Page index.")
    selector: str = Field(..., description="CSS selector for the input element.")
    text: str = Field(..., description="Text to type/fill.")

class InputTextOnWebpageResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'selector':..., 'typed_text':...}")
    error: Optional[str] = Field(None, description="If any error.")
    error_code: str = Field(..., description="SUCCESS or error type.")