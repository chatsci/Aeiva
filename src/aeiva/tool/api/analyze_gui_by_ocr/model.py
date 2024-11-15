# tools/analyze_gui_by_ocr/model.py

from pydantic import BaseModel, Field, confloat
from typing import Optional, List, Dict, Any

class AnalyzeGuiByOcrErrorCode:
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SUCCESS = "SUCCESS"

class AnalyzeGuiByOcrParams(BaseModel):
    target_text: Optional[str] = Field(None, description="Optional text to filter OCR results.")
    template_names: Optional[List[str]] = Field(None, description="Optional list of template image names to filter template matching results (without extension).")
    template_path: Optional[str] = Field(None, description="The path to the directory containing template images. If not provided, reads from GUI_TEMPLATES_IMG_PATH environment variable.")
    threshold: Optional[float] = Field(0.8, description="The matching threshold between 0 and 1 for template matching.")

class AnalyzeGuiByOcrResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Results of OCR and template matching.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")