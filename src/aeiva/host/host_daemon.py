from __future__ import annotations

import os
import secrets
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from aeiva.host.host_runner import HostRunner
from aeiva.host.command_policy import ShellCommandPolicy

DEFAULT_AUTH_TOKEN_ENV_VAR = "AEIVA_HOST_DAEMON_TOKEN"


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


def _resolve_auth_token(auth_token: Optional[str], auth_token_env_var: Optional[str]) -> Optional[str]:
    if isinstance(auth_token, str) and auth_token.strip():
        return auth_token.strip()
    env_var = (auth_token_env_var or DEFAULT_AUTH_TOKEN_ENV_VAR).strip()
    if not env_var:
        return None
    value = os.getenv(env_var)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    value = authorization.strip()
    if not value.lower().startswith("bearer "):
        return None
    token = value[7:].strip()
    return token or None


def build_app(
    allowed_tools: Optional[list[str]] = None,
    command_policy: Optional[ShellCommandPolicy] = None,
    auth_token: Optional[str] = None,
    auth_token_env_var: Optional[str] = None,
    require_auth: bool = True,
) -> FastAPI:
    resolved_auth_token = _resolve_auth_token(auth_token, auth_token_env_var)
    if require_auth and not resolved_auth_token:
        env_var = (auth_token_env_var or DEFAULT_AUTH_TOKEN_ENV_VAR).strip()
        raise ValueError(
            "Host daemon auth token missing. Configure "
            f"`auth_token` or set env var `{env_var}`."
        )

    app = FastAPI(title="Aeiva Host Daemon", version="0.1")
    runner = HostRunner(allowed_tools=allowed_tools, command_policy=command_policy)

    @app.get("/info")
    async def info() -> Dict[str, Any]:
        return {
            "ok": True,
            "allowed_tools": allowed_tools or "all",
            "shell_policy": command_policy.mode if command_policy else "allow_all",
            "auth_required": require_auth,
        }

    @app.post("/invoke", response_model=InvokeResponse)
    async def invoke(
        req: InvokeRequest,
        authorization: Optional[str] = Header(default=None, alias="Authorization"),
    ) -> InvokeResponse:
        if require_auth:
            presented_token = _extract_bearer_token(authorization)
            expected_token = resolved_auth_token or ""
            if not presented_token or not secrets.compare_digest(presented_token, expected_token):
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        try:
            result = await runner.execute(req.tool, req.args or {})
            return InvokeResponse(ok=True, id=req.id, result=result)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except Exception as exc:
            return InvokeResponse(ok=False, id=req.id, error=str(exc))

    return app
