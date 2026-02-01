from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .aeiva_adapter import generate_patch

router = APIRouter()

class TaskSpec(BaseModel):
    language: str
    intent: str
    selectionText: str
    offsetStart: int
    offsetEnd: int
    preContext: Optional[str] = None
    postContext: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    projectRoot: Optional[str] = None

@router.get("/health")
def health():
    return {"ok": True}

@router.post("/patch")
def patch(spec: TaskSpec):
    patch = generate_patch(spec.model_dump())
    return patch