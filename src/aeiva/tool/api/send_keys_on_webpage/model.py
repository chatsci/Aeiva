from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SendKeysOnWebpageErrorCode:
    SUCCESS = "SUCCESS"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    SEND_KEYS_FAILED = "SEND_KEYS_FAILED"

class SendKeysOnWebpageParams(BaseModel):
    page_id: int = Field(..., description="Page index.")
    selector: str = Field("", description="CSS selector for the target, or empty for body.")
    keys: List[str] = Field(..., description="List of key strings (e.g. Enter, Tab).")

class SendKeysOnWebpageResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'selector':..., 'keys':...}")
    error: Optional[str] = Field(None, description="Error if any.")
    error_code: str = Field(..., description="SUCCESS or error code.")