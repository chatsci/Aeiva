from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from aeiva.host.host_runner import HostRunner


class InvokeRequest(BaseModel):
    tool: str
    args: Dict[str, Any] = {}
    id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class InvokeResponse(BaseModel):
    ok: bool
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None


def build_app(allowed_tools: Optional[list[str]] = None) -> FastAPI:
    app = FastAPI(title="Aeiva Host Daemon", version="0.1")
    runner = HostRunner(allowed_tools=allowed_tools)

    @app.get("/info")
    async def info() -> Dict[str, Any]:
        return {
            "ok": True,
            "allowed_tools": allowed_tools or "all",
        }

    @app.post("/invoke", response_model=InvokeResponse)
    async def invoke(req: InvokeRequest) -> InvokeResponse:
        try:
            result = await runner.execute(req.tool, req.args or {})
            return InvokeResponse(ok=True, id=req.id, result=result)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except Exception as exc:
            return InvokeResponse(ok=False, id=req.id, error=str(exc))

    return app
