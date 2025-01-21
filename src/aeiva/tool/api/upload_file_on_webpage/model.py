from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class UploadFileOnWebpageErrorCode:
    SUCCESS = "SUCCESS"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    UPLOAD_FILE_FAILED = "UPLOAD_FILE_FAILED"

class UploadFileOnWebpageParams(BaseModel):
    page_id: int = Field(..., description="Index of the page.")
    selector: str = Field(..., description="CSS selector for the <input type='file'>.")
    file_path: str = Field(..., description="Local file path to upload.")

class UploadFileOnWebpageResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'selector':..., 'file_path':...}")
    error: Optional[str] = Field(None, description="Error if any.")
    error_code: str = Field(..., description="SUCCESS or error code.")