from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SelectDropdownOnWebpageErrorCode:
    SUCCESS = "SUCCESS"
    SELECT_DROPDOWN_FAILED = "SELECT_DROPDOWN_FAILED"

class SelectDropdownOnWebpageParams(BaseModel):
    page_id: int = Field(..., description="Page index.")
    selector: str = Field(..., description="CSS selector for the <select> element.")
    value: str = Field(..., description="Value of the option to select.")

class SelectDropdownOnWebpageResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'selector':..., 'value':...}")
    error: Optional[str] = Field(None, description="Error if any.")
    error_code: str = Field(..., description="SUCCESS or failure code.")