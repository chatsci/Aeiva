from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import time
from dataclasses import dataclass, replace
from typing import Any, ClassVar, Optional
from urllib.parse import urlparse

import httpx
import numpy as np

try:
    from fastrtc import AsyncAudioVideoStreamHandler, AdditionalOutputs
except ImportError:  # pragma: no cover - optional dependency
    try:
        # Backward compatibility for environments still using gradio-webrtc.
        from gradio_webrtc import AsyncAudioVideoStreamHandler, AdditionalOutputs  # type: ignore
    except ImportError:
        AsyncAudioVideoStreamHandler = object  # type: ignore
        AdditionalOutputs = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class MiniCPMLiveConfig:
    """
    Config for MiniCPM Omni HTTP streaming bridge.
    """

    base_url: str = "http://127.0.0.1:9060"
    language: str = "zh"
    duplex_mode: bool = True
    high_quality_mode: bool = False
    high_fps_mode: bool = False
    send_video: bool = True
    video_fps: float = 1.0
    output_sample_rate: int = 24000
    output_frame_size: int = 960
    input_sample_rate: int = 24000
    prefill_audio_chunk_ms: int = 240
    request_timeout: float = 20.0
    auto_break_on_barge_in: bool = True
    prefill_flush_idle_ms: int = 180
    text_fallback_enabled: bool = True
    text_fallback_base_url: str = "http://127.0.0.1:8022/v1"
    text_fallback_model: str = "openbmb/MiniCPM-o-4_5"
    text_fallback_timeout: float = 30.0
    text_fallback_retries: int = 3
    text_fallback_retry_backoff_seconds: float = 0.4
    text_fallback_allow_direct_port_discovery: bool = False
    service_registry_enabled: bool = False
    init_retries: int = 3
    init_retry_backoff_seconds: float = 0.6


class MiniCPMOmniClient:
    """
    HTTP client for MiniCPM WebRTC_Demo omni endpoints.

    Endpoints:
    - POST /omni/init_sys_prompt
    - POST /omni/streaming_prefill
    - POST /omni/streaming_generate  (SSE)
    - POST /omni/break
    - POST /omni/stop
    """

    def __init__(
        self,
        config: MiniCPMLiveConfig,
        audio_queue: asyncio.Queue,
        text_queue: asyncio.Queue,
    ) -> None:
        self.config = config
        self.audio_queue = audio_queue
        self.text_queue = text_queue
        self._client = self._build_http_client()
        self._text_client = self._build_text_http_client()
        self._session_ready = False
        self._session_id: Optional[str] = None
        self._session_lock = asyncio.Lock()
        self._prefill_lock = asyncio.Lock()
        self._image_audio_id = 0
        self._generate_lock = asyncio.Lock()
        self._text_lock = asyncio.Lock()
        self._generating = False
        self._generate_has_output = False
        self._resolved_text_model_id: Optional[str] = None
        self._configured_text_fallback_base_url = self._normalize_openai_base_url(
            self.config.text_fallback_base_url
        )

    def _build_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"Connection": "close"},
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=20),
            timeout=httpx.Timeout(
                connect=float(self.config.request_timeout),
                read=None,
                write=float(self.config.request_timeout),
                pool=float(self.config.request_timeout),
            )
        )

    def _build_text_http_client(self) -> httpx.AsyncClient:
        timeout = max(0.5, float(self.config.text_fallback_timeout))
        return httpx.AsyncClient(
            headers={"Connection": "close"},
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=10),
            timeout=httpx.Timeout(
                connect=timeout,
                read=timeout,
                write=timeout,
                pool=timeout,
            )
        )

    @property
    def generating(self) -> bool:
        return self._generating

    @property
    def generating_with_output(self) -> bool:
        return self._generating and self._generate_has_output

    @staticmethod
    def _format_exception(exc: Exception) -> str:
        detail = str(exc).strip()
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code if exc.response is not None else "unknown"
            url = str(exc.request.url) if exc.request is not None else "unknown"
            body = ""
            if exc.response is not None:
                try:
                    raw_body = (exc.response.text or "").strip()
                except Exception:
                    raw_body = ""
                if raw_body:
                    compact = " ".join(raw_body.split())
                    body = f" | body={compact[:240]}"
            return f"HTTP {status} at {url}{body}"
        if detail:
            return f"{exc.__class__.__name__}: {detail}"
        return exc.__class__.__name__

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        if isinstance(
            exc,
            (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.WriteError,
            ),
        ):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                return int(exc.response.status_code) >= 500
            except Exception:
                return False
        return False

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        if not isinstance(exc, httpx.HTTPStatusError):
            return False
        if exc.response is None:
            return False
        try:
            status = int(exc.response.status_code)
        except Exception:
            return False
        return status in {404, 405}

    @staticmethod
    def _extract_error_body_text(exc: Exception) -> str:
        if not isinstance(exc, httpx.HTTPStatusError):
            return str(exc or "").strip().lower()
        if exc.response is None:
            return str(exc or "").strip().lower()
        try:
            body = (exc.response.text or "").strip().lower()
        except Exception:
            body = ""
        return body or str(exc or "").strip().lower()

    def _should_recover_omni_session(self, exc: Exception) -> bool:
        if self._is_retryable_error(exc):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                status = int(exc.response.status_code)
            except Exception:
                status = 0
            if status in {400, 404, 409, 410, 422, 503}:
                body = self._extract_error_body_text(exc)
                markers = (
                    "未找到活跃会话",
                    "active session",
                    "init_sys_prompt",
                    "service unavailable",
                    "restarting",
                    "please initialize",
                )
                if not body:
                    return status in {503}
                return any(marker in body for marker in markers)
        detail = str(exc or "").strip().lower()
        return any(
            marker in detail
            for marker in (
                "active session",
                "init_sys_prompt",
                "service unavailable",
                "restarting",
                "connection reset",
            )
        )

    def _invalidate_session(self) -> None:
        self._session_ready = False
        self._session_id = None

    async def _reset_http_client(self) -> None:
        await self._reset_omni_http_client()

    async def _reset_omni_http_client(self) -> None:
        if not isinstance(self._client, httpx.AsyncClient):
            return
        old_client = self._client
        self._client = self._build_http_client()
        try:
            await old_client.aclose()
        except Exception:
            pass

    async def _reset_text_http_client(self) -> None:
        if not isinstance(self._text_client, httpx.AsyncClient):
            return
        old_client = self._text_client
        self._text_client = self._build_text_http_client()
        try:
            await old_client.aclose()
        except Exception:
            pass

    async def ensure_session(self) -> None:
        if self._session_ready:
            return
        async with self._session_lock:
            if self._session_ready:
                return
            payload = {
                "media_type": "omni",
                "duplex_mode": bool(self.config.duplex_mode),
                "high_quality_mode": bool(self.config.high_quality_mode),
                "high_fps_mode": bool(self.config.high_fps_mode),
                "language": self.config.language,
            }
            attempts = max(1, int(self.config.init_retries))
            base_backoff = max(0.1, float(self.config.init_retry_backoff_seconds))
            last_error: Optional[Exception] = None
            for attempt in range(1, attempts + 1):
                try:
                    init_url = f"{self.config.base_url.rstrip('/')}/omni/init_sys_prompt"
                    resp = await self._client.post(init_url, json=payload)
                    resp.raise_for_status()
                    data = resp.json() if resp.content else {}
                    if isinstance(data, dict):
                        self._session_id = data.get("session_id")
                    self._session_ready = True
                    return
                except Exception as e:
                    last_error = e
                    if attempt >= attempts:
                        break
                    if self._is_retryable_error(e):
                        if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError)):
                            await self._reset_omni_http_client()
                        discovered = await self._discover_omni_base_url(payload)
                        if discovered:
                            return
                    backoff = min(3.0, base_backoff * (2 ** (attempt - 1)))
                    await asyncio.sleep(backoff)
            assert last_error is not None
            raise RuntimeError(
                "MiniCPM session init failed: "
                f"{self._format_exception(last_error)}"
            ) from last_error

    async def _post_omni_json(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        timeout: Optional[float] = None,
        allow_session_recovery: bool = True,
    ) -> httpx.Response:
        attempts = 2 if allow_session_recovery else 1
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            await self.ensure_session()
            try:
                resp = await self._client.post(
                    f"{self.config.base_url.rstrip('/')}{endpoint}",
                    json=payload,
                    timeout=timeout,
                )
                resp.raise_for_status()
                return resp
            except Exception as e:
                last_error = e
                should_retry = attempt < attempts and self._should_recover_omni_session(e)
                if not should_retry:
                    break
                self._invalidate_session()
                if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError)):
                    await self._reset_omni_http_client()
                await asyncio.sleep(0.25)
        assert last_error is not None
        raise last_error

    async def close(self) -> None:
        try:
            await self._client.post(f"{self.config.base_url.rstrip('/')}/omni/stop", json={})
        except Exception:
            pass
        await self._client.aclose()
        if self._text_client is not self._client:
            await self._text_client.aclose()

    @staticmethod
    def _openai_compat_models_url(base_url: str) -> str:
        base = str(base_url or "").strip().rstrip("/")
        if not base:
            return ""
        if base.endswith("/models"):
            return base
        if base.endswith("/v1"):
            return f"{base}/models"
        return f"{base}/v1/models"

    @staticmethod
    def _openai_compat_chat_url(base_url: str) -> str:
        base = str(base_url or "").strip().rstrip("/")
        if not base:
            return ""
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    @staticmethod
    def _normalize_openai_base_url(base_url: str) -> str:
        base = str(base_url or "").strip().rstrip("/")
        if not base:
            return ""
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        elif base.endswith("/models"):
            base = base[: -len("/models")]
        if base.endswith("/v1"):
            return base
        return f"{base}/v1"

    @staticmethod
    def _build_openai_v1_base_url(*, scheme: str, host: str, port: int) -> str:
        normalized_scheme = (scheme or "http").lower()
        normalized_host = str(host or "").strip()
        if not normalized_host:
            return ""
        if ":" in normalized_host and not normalized_host.startswith("["):
            normalized_host = f"[{normalized_host}]"
        return f"{normalized_scheme}://{normalized_host}:{int(port)}/v1"

    @staticmethod
    def _build_http_base_url(*, scheme: str, host: str, port: int) -> str:
        normalized_scheme = (scheme or "http").lower()
        normalized_host = str(host or "").strip()
        if not normalized_host:
            return ""
        if ":" in normalized_host and not normalized_host.startswith("["):
            normalized_host = f"[{normalized_host}]"
        return f"{normalized_scheme}://{normalized_host}:{int(port)}"

    @staticmethod
    def _dedupe_candidates(candidates: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate or "").strip().rstrip("/")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(key)
        return deduped

    def _iter_backend_registry_base_candidates(self) -> list[str]:
        candidates: list[str] = []
        configured = self._normalize_openai_base_url(self.config.text_fallback_base_url)
        pinned = self._configured_text_fallback_base_url
        for openai_base in (configured, pinned):
            parsed = urlparse(openai_base) if openai_base else None
            if parsed and parsed.hostname and parsed.port:
                backend_base = self._build_http_base_url(
                    scheme=parsed.scheme or "http",
                    host=parsed.hostname,
                    port=int(parsed.port),
                )
                if backend_base:
                    candidates.append(backend_base)

        base_parsed = urlparse(str(self.config.base_url or "").strip())
        if base_parsed and base_parsed.hostname:
            for backend_port in range(8021, 8031):
                backend_base = self._build_http_base_url(
                    scheme=base_parsed.scheme or "http",
                    host=base_parsed.hostname,
                    port=backend_port,
                )
                if backend_base:
                    candidates.append(backend_base)

        return self._dedupe_candidates(candidates)

    async def _discover_registered_service_endpoints(self) -> tuple[list[str], list[str]]:
        if not bool(self.config.service_registry_enabled):
            return [], []

        probe_timeout = min(
            1.2,
            float(self.config.request_timeout),
            float(self.config.text_fallback_timeout),
        )
        probe_timeout = max(0.3, probe_timeout)

        discovered_omni: list[str] = []
        discovered_text: list[str] = []

        for backend_base in self._iter_backend_registry_base_candidates():
            services_url = f"{backend_base.rstrip('/')}/api/inference/services?available_only=true"
            try:
                resp = await self._text_client.get(services_url, timeout=probe_timeout)
                resp.raise_for_status()
                payload = resp.json() if resp.content else {}
                services = payload.get("services") if isinstance(payload, dict) else None
                if not isinstance(services, list):
                    continue
            except Exception:
                continue

            parsed = urlparse(backend_base)
            fallback_host = parsed.hostname or ""
            scheme = parsed.scheme or "http"

            for service in services:
                if not isinstance(service, dict):
                    continue
                raw_port = service.get("port") or service.get("model_port")
                try:
                    service_port = int(raw_port)
                except Exception:
                    continue

                host_candidates: list[str] = []
                if fallback_host:
                    host_candidates.append(fallback_host)
                service_ip = str(service.get("ip") or "").strip()
                if service_ip:
                    host_candidates.append(service_ip)

                for host_candidate in host_candidates:
                    omni_base = self._build_http_base_url(
                        scheme=scheme,
                        host=host_candidate,
                        port=service_port,
                    )
                    if omni_base:
                        discovered_omni.append(omni_base)

                    text_base = self._build_openai_v1_base_url(
                        scheme=scheme,
                        host=host_candidate,
                        port=service_port + 10000,
                    )
                    if text_base:
                        discovered_text.append(text_base)

        return self._dedupe_candidates(discovered_omni), self._dedupe_candidates(discovered_text)

    @staticmethod
    def _extract_model_id_from_models_payload(payload: Any) -> Optional[str]:
        candidates = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(candidates, list) or not candidates:
            return None
        first = candidates[0] if isinstance(candidates[0], dict) else {}
        model_id = first.get("id") or first.get("model") or first.get("name")
        if isinstance(model_id, str) and model_id.strip():
            return model_id.strip()
        return None

    def _iter_text_base_url_candidates(self) -> list[str]:
        candidates: list[str] = []

        configured = self._normalize_openai_base_url(self.config.text_fallback_base_url)
        pinned = self._configured_text_fallback_base_url
        if configured:
            candidates.append(configured)
        if pinned and pinned != configured:
            candidates.append(pinned)

        configured_parsed = urlparse(configured) if configured else None
        pinned_parsed = urlparse(pinned) if pinned else None
        base_parsed = urlparse(str(self.config.base_url or "").strip())

        ref_scheme = (
            (configured_parsed.scheme if configured_parsed else "")
            or (pinned_parsed.scheme if pinned_parsed else "")
            or (base_parsed.scheme or "http")
        )
        ref_host = (
            (configured_parsed.hostname if configured_parsed else "")
            or (pinned_parsed.hostname if pinned_parsed else "")
            or base_parsed.hostname
        )
        ref_port = (
            (configured_parsed.port if configured_parsed else None)
            or (pinned_parsed.port if pinned_parsed else None)
        )

        if ref_host and ref_port:
            # Prefer nearby backend ports first (official oneclick backend auto-allocates 8021+).
            for offset in range(1, 9):
                plus = self._build_openai_v1_base_url(
                    scheme=ref_scheme,
                    host=ref_host,
                    port=int(ref_port) + offset,
                )
                if plus:
                    candidates.append(plus)
            for offset in range(1, 5):
                lowered = int(ref_port) - offset
                if lowered > 0:
                    minus = self._build_openai_v1_base_url(
                        scheme=ref_scheme,
                        host=ref_host,
                        port=lowered,
                    )
                    if minus:
                        candidates.append(minus)

        if base_parsed.hostname and base_parsed.port:
            derived_port = int(base_parsed.port) + 10000
            derived = self._build_openai_v1_base_url(
                scheme=base_parsed.scheme or "http",
                host=base_parsed.hostname,
                port=derived_port,
            )
            if derived:
                candidates.append(derived)
            for offset in range(1, 9):
                plus = self._build_openai_v1_base_url(
                    scheme=base_parsed.scheme or "http",
                    host=base_parsed.hostname,
                    port=derived_port + offset,
                )
                if plus:
                    candidates.append(plus)
                minus_port = derived_port - offset
                if minus_port > 0:
                    minus = self._build_openai_v1_base_url(
                        scheme=base_parsed.scheme or "http",
                        host=base_parsed.hostname,
                        port=minus_port,
                    )
                    if minus:
                        candidates.append(minus)

        if ref_host:
            for backend_port in range(8021, 8031):
                shifted = self._build_openai_v1_base_url(
                    scheme=ref_scheme,
                    host=ref_host,
                    port=backend_port,
                )
                if shifted:
                    candidates.append(shifted)

        # Optional direct llama-server discovery; disabled by default to avoid unstable endpoint drift.
        if (
            bool(self.config.text_fallback_allow_direct_port_discovery)
            and base_parsed.hostname
            and base_parsed.port
        ):
            derived_port = int(base_parsed.port) + 10000
            for offset in range(9, 33):
                shifted = self._build_openai_v1_base_url(
                    scheme=base_parsed.scheme or "http",
                    host=base_parsed.hostname,
                    port=derived_port + offset,
                )
                if shifted:
                    candidates.append(shifted)
        return self._dedupe_candidates(candidates)

    async def _discover_text_fallback_base_url(self) -> Optional[str]:
        probe_timeout = min(0.8, float(self.config.text_fallback_timeout))
        _, registry_text_candidates = await self._discover_registered_service_endpoints()
        ordered_candidates = self._dedupe_candidates(
            [*registry_text_candidates, *self._iter_text_base_url_candidates()]
        )
        for candidate in ordered_candidates:
            models_url = self._openai_compat_models_url(candidate)
            if not models_url:
                continue
            try:
                resp = await self._text_client.get(models_url, timeout=probe_timeout)
                resp.raise_for_status()
                payload = resp.json() if resp.content else {}
                model_id = self._extract_model_id_from_models_payload(payload)
                if not model_id:
                    continue
            except Exception:
                continue
            self.config.text_fallback_base_url = candidate
            self._resolved_text_model_id = model_id
            return candidate
        return None

    def _iter_omni_base_url_candidates(self) -> list[str]:
        candidates: list[str] = []
        configured = str(self.config.base_url or "").strip().rstrip("/")
        if configured:
            candidates.append(configured)
        parsed = urlparse(configured) if configured else None
        if parsed and parsed.hostname and parsed.port:
            for offset in range(1, 33):
                shifted = self._build_http_base_url(
                    scheme=parsed.scheme or "http",
                    host=parsed.hostname,
                    port=int(parsed.port) + offset,
                )
                if shifted:
                    candidates.append(shifted)

        text_base = self._normalize_openai_base_url(self.config.text_fallback_base_url)
        text_parsed = urlparse(text_base) if text_base else None
        if text_parsed and text_parsed.hostname and text_parsed.port:
            derived_port = int(text_parsed.port) - 10000
            if derived_port > 0:
                derived = self._build_http_base_url(
                    scheme=text_parsed.scheme or "http",
                    host=text_parsed.hostname,
                    port=derived_port,
                )
                if derived:
                    candidates.append(derived)
                for offset in range(1, 33):
                    shifted = self._build_http_base_url(
                        scheme=text_parsed.scheme or "http",
                        host=text_parsed.hostname,
                        port=derived_port + offset,
                    )
                    if shifted:
                        candidates.append(shifted)

        return self._dedupe_candidates(candidates)

    async def _discover_omni_base_url(self, payload: dict[str, Any]) -> Optional[str]:
        probe_timeout = min(1.2, float(self.config.request_timeout))
        registry_omni_candidates, _ = await self._discover_registered_service_endpoints()
        ordered_candidates = self._dedupe_candidates(
            [*registry_omni_candidates, *self._iter_omni_base_url_candidates()]
        )
        for candidate in ordered_candidates:
            init_url = f"{candidate.rstrip('/')}/omni/init_sys_prompt"
            try:
                resp = await self._client.post(init_url, json=payload, timeout=probe_timeout)
                resp.raise_for_status()
                data = resp.json() if resp.content else {}
                if isinstance(data, dict):
                    self._session_id = data.get("session_id")
            except Exception:
                continue
            self.config.base_url = candidate.rstrip("/")
            self._session_ready = True
            return self.config.base_url
        return None

    async def _resolve_text_model_id(self) -> Optional[str]:
        if self._resolved_text_model_id:
            return self._resolved_text_model_id
        models_url = self._openai_compat_models_url(self.config.text_fallback_base_url)
        if not models_url:
            return None
        try:
            resp = await self._text_client.get(
                models_url,
                timeout=float(self.config.text_fallback_timeout),
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            return None
        model_id = self._extract_model_id_from_models_payload(payload)
        if model_id:
            self._resolved_text_model_id = model_id
            return self._resolved_text_model_id
        return None

    @staticmethod
    def _extract_text_from_chat_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
                elif isinstance(item, str) and item:
                    parts.append(item)
            return "".join(parts).strip()
        return ""

    async def generate_text_reply(self, user_text: str) -> str:
        if not self.config.text_fallback_enabled:
            return "Text input is disabled for MiniCPM live mode."
        async with self._text_lock:
            attempts = max(1, int(self.config.text_fallback_retries))
            base_backoff = max(0.05, float(self.config.text_fallback_retry_backoff_seconds))
            last_error: Optional[Exception] = None
            for attempt in range(1, attempts + 1):
                try:
                    chat_url = self._openai_compat_chat_url(self.config.text_fallback_base_url)
                    if not chat_url:
                        raise RuntimeError("text_fallback_base_url is empty")

                    resolved_model = await self._resolve_text_model_id()
                    model_name = resolved_model or str(self.config.text_fallback_model or "").strip()
                    if not model_name:
                        model_name = "openbmb/MiniCPM-o-4_5"

                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": str(user_text)}],
                        "temperature": 0.2,
                        "stream": False,
                    }
                    resp = await self._text_client.post(
                        chat_url,
                        json=payload,
                        timeout=float(self.config.text_fallback_timeout),
                    )
                    resp.raise_for_status()
                    data = resp.json() if resp.content else {}
                    choices = data.get("choices") if isinstance(data, dict) else None
                    if not isinstance(choices, list) or not choices:
                        raise RuntimeError("No choices returned from text fallback endpoint")
                    first = choices[0] if isinstance(choices[0], dict) else {}
                    message = first.get("message") if isinstance(first, dict) else {}
                    content = message.get("content") if isinstance(message, dict) else ""
                    text = self._extract_text_from_chat_content(content).strip()
                    if not text:
                        raise RuntimeError("Empty text content from text fallback endpoint")
                    return text
                except Exception as e:
                    last_error = e
                    endpoint_not_found = self._is_not_found_error(e)
                    should_retry = attempt < attempts and (
                        self._is_retryable_error(e) or endpoint_not_found
                    )
                    if not should_retry:
                        break
                    if endpoint_not_found or isinstance(
                        e,
                        (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError),
                    ):
                        await self._reset_text_http_client()
                        discovered = await self._discover_text_fallback_base_url()
                        if discovered:
                            continue
                    backoff = min(2.0, base_backoff * (2 ** (attempt - 1)))
                    await asyncio.sleep(backoff)

            assert last_error is not None
            raise RuntimeError(
                "MiniCPM text fallback request failed: "
                f"{self._format_exception(last_error)}"
            ) from last_error

    @staticmethod
    def _encode_wav_base64(sample_rate: int, audio_array: np.ndarray) -> str:
        import soundfile as sf

        array = np.asarray(audio_array)
        if array.ndim > 1:
            array = np.squeeze(array)
        if array.dtype == np.int16:
            audio_float = array.astype(np.float32) / 32768.0
        else:
            audio_float = array.astype(np.float32)
            audio_float = np.clip(audio_float, -1.0, 1.0)

        buf = io.BytesIO()
        sf.write(buf, audio_float, int(sample_rate), format="WAV", subtype="PCM_16")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def _encode_image_base64(frame: np.ndarray) -> str:
        from PIL import Image

        image = np.asarray(frame)
        if image.dtype != np.uint8:
            if np.issubdtype(image.dtype, np.floating):
                image = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
            else:
                image = image.astype(np.uint8)
        pil_image = Image.fromarray(image)
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    async def prefill(
        self,
        *,
        audio: Optional[tuple[int, np.ndarray]] = None,
        image: Optional[np.ndarray] = None,
    ) -> None:
        payload: dict[str, Any] = {}

        if audio is not None:
            sample_rate, audio_np = audio
            if audio_np is not None and np.asarray(audio_np).size > 0:
                payload["audio"] = self._encode_wav_base64(sample_rate, audio_np)

        if image is not None:
            payload["image"] = self._encode_image_base64(image)
            payload["image_audio_id"] = self._image_audio_id
            payload["frame_index"] = 0
            self._image_audio_id += 1

        if not payload:
            return
        async with self._prefill_lock:
            await self._post_omni_json(
                endpoint="/omni/streaming_prefill",
                payload=payload,
                timeout=float(self.config.request_timeout),
                allow_session_recovery=True,
            )

    async def break_generation(self) -> None:
        try:
            await self._client.post(f"{self.config.base_url.rstrip('/')}/omni/break", json={})
        except Exception:
            logger.debug("MiniCPM break request failed", exc_info=True)

    async def stream_generate_once(self) -> None:
        async with self._generate_lock:
            self._generating = True
            self._generate_has_output = False
            try:
                attempts = 2
                for attempt in range(1, attempts + 1):
                    try:
                        await self.ensure_session()
                        async with self._client.stream(
                            "POST",
                            f"{self.config.base_url.rstrip('/')}/omni/streaming_generate",
                            json={},
                        ) as resp:
                            resp.raise_for_status()
                            async for line in resp.aiter_lines():
                                if not line:
                                    continue
                                if not line.startswith("data:"):
                                    continue
                                raw = line[5:].strip()
                                if not raw:
                                    continue
                                if raw == "[DONE]":
                                    self.text_queue.put_nowait("<END_OF_RESPONSE>")
                                    break
                                try:
                                    event = json.loads(raw)
                                except json.JSONDecodeError:
                                    continue

                                if isinstance(event, dict) and event.get("error"):
                                    await self.text_queue.put(f"MiniCPM error: {event['error']}")
                                    continue

                                chunk = event.get("chunk_data") if isinstance(event, dict) else None
                                if isinstance(chunk, dict):
                                    wav_b64 = chunk.get("wav")
                                    if isinstance(wav_b64, str) and wav_b64:
                                        sample_rate = int(chunk.get("sample_rate") or self.config.output_sample_rate)
                                        audio_bytes = base64.b64decode(wav_b64)
                                        if len(audio_bytes) >= 4 and audio_bytes[:4] == b"RIFF":
                                            import soundfile as sf

                                            audio_array, decoded_sr = sf.read(
                                                io.BytesIO(audio_bytes),
                                                dtype="int16",
                                            )
                                            if np.asarray(audio_array).ndim > 1:
                                                audio_array = np.squeeze(np.asarray(audio_array))
                                            sample_rate = int(decoded_sr or sample_rate)
                                            audio_array = np.asarray(audio_array, dtype=np.int16)
                                        else:
                                            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                                        self.audio_queue.put_nowait((sample_rate, audio_array))
                                        self._generate_has_output = True
                                    text = chunk.get("text")
                                    if isinstance(text, str) and text:
                                        self.text_queue.put_nowait(text)
                                        self._generate_has_output = True

                                if isinstance(event, dict) and event.get("done"):
                                    self.text_queue.put_nowait("<END_OF_RESPONSE>")
                                    break
                        break
                    except Exception as e:
                        should_retry = attempt < attempts and self._should_recover_omni_session(e)
                        if not should_retry:
                            raise
                        self._invalidate_session()
                        if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError)):
                            await self._reset_omni_http_client()
                        await asyncio.sleep(0.25)
            finally:
                self._generating = False
                self._generate_has_output = False


class MiniCPMOmniRealtimeHandler(AsyncAudioVideoStreamHandler):
    """
    Gradio WebRTC handler for MiniCPM Omni HTTP backend.
    """

    _active_instance: ClassVar[Optional["MiniCPMOmniRealtimeHandler"]] = None

    def __init__(self, config: MiniCPMLiveConfig):
        if AsyncAudioVideoStreamHandler is object:
            raise RuntimeError(
                "fastrtc is required for live realtime mode. "
                "Install with: pip install -e '.[realtime]'"
            )
        self.config = config
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.text_queue: asyncio.Queue = asyncio.Queue()
        self.client = MiniCPMOmniClient(config, self.audio_queue, self.text_queue)
        self.chatbot = []
        self.assistant_active = False
        self._session_ready = False
        self._generate_task: Optional[asyncio.Task] = None
        self._video_prefill_task: Optional[asyncio.Task] = None
        self._audio_buffer: list[np.ndarray] = []
        self._audio_buffer_samples = 0
        self._video_frame_queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=1)
        self._latest_video_frame: Optional[np.ndarray] = None
        self._current_input_sample_rate = int(self.config.input_sample_rate)
        self._target_buffer_samples = int(
            max(40, self._current_input_sample_rate * max(80, self.config.prefill_audio_chunk_ms) / 1000.0)
        )
        self._last_video_sent_at = 0.0
        self._last_break_at = 0.0
        self._last_audio_input_at = 0.0
        self._flush_idle_seconds = max(
            0.06,
            float(max(0, int(self.config.prefill_flush_idle_ms))) / 1000.0,
        )
        self._last_webrtc_submit_key: Optional[tuple[str, str]] = None
        self._last_runtime_error: Optional[str] = None
        self._closed = False
        super().__init__(
            expected_layout="mono",
            output_sample_rate=int(self.config.output_sample_rate),
            input_sample_rate=int(self.config.input_sample_rate),
        )

    def copy(self) -> "MiniCPMOmniRealtimeHandler":
        cloned = MiniCPMOmniRealtimeHandler(replace(self.config))
        MiniCPMOmniRealtimeHandler._active_instance = cloned
        return cloned

    @classmethod
    def get_active(cls) -> Optional["MiniCPMOmniRealtimeHandler"]:
        instance = cls._active_instance
        if instance is None:
            return None
        if not instance.is_available():
            if cls._active_instance is instance:
                cls._active_instance = None
            return None
        return instance

    def is_available(self) -> bool:
        return not self._closed

    def _publish_runtime_error(self, error: Exception | str) -> None:
        detail = (
            MiniCPMOmniClient._format_exception(error)
            if isinstance(error, Exception)
            else str(error).strip()
        )
        if not detail:
            detail = "unknown runtime error"
        if detail == self._last_runtime_error:
            return
        self._last_runtime_error = detail
        message = f"[MiniCPM runtime error] {detail}"
        try:
            self.text_queue.put_nowait(message)
        except Exception:
            pass
        logger.error(message)

    async def _ensure_ready(self) -> None:
        if self._closed:
            raise RuntimeError("MiniCPM handler is closed")
        if self._session_ready:
            return
        await self.client.ensure_session()
        self._session_ready = True
        self._last_runtime_error = None
        self._ensure_video_prefill_task()

    async def start_up(self) -> None:
        self._closed = False
        try:
            await self._ensure_ready()
        except Exception as e:
            self._publish_runtime_error(e)

    def _ensure_video_prefill_task(self) -> None:
        if not self.config.send_video:
            return
        if self._video_prefill_task is not None and not self._video_prefill_task.done():
            return
        self._video_prefill_task = asyncio.create_task(self._video_prefill_loop())

    def _ensure_generate_task(self) -> None:
        if self._generate_task is not None and not self._generate_task.done():
            return
        self._generate_task = asyncio.create_task(self._generate_loop())

    async def _generate_loop(self) -> None:
        try:
            await self.client.stream_generate_once()
        except Exception as e:
            self._publish_runtime_error(e)
            self.text_queue.put_nowait(f"MiniCPM generate error: {e}")
            self.text_queue.put_nowait("<END_OF_RESPONSE>")

    def _enqueue_video_frame(self, frame: Any) -> None:
        if not self.config.send_video or frame is None:
            return
        frame_np = np.asarray(frame)
        if frame_np.size == 0:
            return
        if self._video_frame_queue.full():
            try:
                self._video_frame_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            self._video_frame_queue.put_nowait(frame_np)
        except asyncio.QueueFull:
            pass

    async def _video_prefill_loop(self) -> None:
        while True:
            frame = await self._video_frame_queue.get()
            try:
                await self._ensure_ready()
                min_gap = 1.0 / max(0.1, float(self.config.video_fps))
                now = time.time()
                wait_seconds = max(0.0, min_gap - (now - self._last_video_sent_at))
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                await self.client.prefill(image=frame)
                self._last_video_sent_at = time.time()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._publish_runtime_error(e)
                logger.debug("MiniCPM video prefill failed: %s", e)

    async def _flush_audio_buffer(self, *, force: bool = False) -> None:
        if self._audio_buffer_samples <= 0:
            return
        if not force and self._audio_buffer_samples < self._target_buffer_samples:
            return

        joined = np.concatenate(self._audio_buffer, axis=0)
        self._audio_buffer.clear()
        self._audio_buffer_samples = 0
        await self.client.prefill(audio=(self._current_input_sample_rate, joined))
        self._ensure_generate_task()

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        try:
            await self._ensure_ready()
            sample_rate, array = frame
            audio = np.asarray(array)
            if audio.ndim > 1:
                audio = np.squeeze(audio)
            if audio.size == 0:
                return

            if self.config.auto_break_on_barge_in and self.client.generating_with_output:
                now = time.time()
                if now - self._last_break_at > 0.35:
                    await self.client.break_generation()
                    self._last_break_at = now

            self._audio_buffer.append(audio)
            self._audio_buffer_samples += int(audio.size)
            self._last_audio_input_at = time.time()
            if int(sample_rate) != int(self._current_input_sample_rate):
                self._current_input_sample_rate = int(sample_rate)
                self._target_buffer_samples = int(
                    max(40, self._current_input_sample_rate * max(80, self.config.prefill_audio_chunk_ms) / 1000.0)
                )
            await self._flush_audio_buffer(force=False)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._publish_runtime_error(e)
            logger.debug("MiniCPM receive failed: %s", e)

    async def video_receive(self, frame: np.ndarray) -> None:
        try:
            if not self.config.send_video:
                return
            frame_np = np.asarray(frame)
            if frame_np.size > 0:
                self._latest_video_frame = frame_np
            self._enqueue_video_frame(frame)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._publish_runtime_error(e)
            logger.debug("MiniCPM video_receive failed: %s", e)

    def update_latest_frame(self, frame: Any) -> Any:
        self._enqueue_video_frame(frame)
        return frame

    async def send_text(self, text: str) -> Optional[str]:
        if not text or not text.strip():
            return None
        if self._closed:
            return "[MiniCPM text fallback error] runtime handler is closed; restart stream and retry."
        try:
            return await self.client.generate_text_reply(text.strip())
        except Exception as e:
            detail = MiniCPMOmniClient._format_exception(e)
            self._publish_runtime_error(detail)
            return f"[MiniCPM text fallback error] {detail}"

    def _resolve_webrtc_data_arg(self) -> Any:
        if not self.latest_args:
            return None
        first = self.latest_args[0]
        if hasattr(first, "textbox") and hasattr(first, "webrtc_id"):
            return first
        for arg in self.latest_args:
            if hasattr(arg, "textbox") and hasattr(arg, "webrtc_id"):
                return arg
        return None

    @staticmethod
    def _is_chat_history_payload(value: Any) -> bool:
        if not isinstance(value, list):
            return False
        for item in value:
            if not isinstance(item, dict):
                return False
            if "role" not in item or "content" not in item:
                return False
            if not isinstance(item.get("role"), str):
                return False
        return True

    def _extract_chat_history_from_args(self) -> Optional[list[dict[str, Any]]]:
        if not self.latest_args or len(self.latest_args) < 2:
            return None
        candidate = self.latest_args[1]
        if not self._is_chat_history_payload(candidate):
            return None
        return [dict(item) for item in candidate]

    async def _consume_webrtc_textbox_submission(self) -> bool:
        webrtc_data = self._resolve_webrtc_data_arg()
        if webrtc_data is None:
            return False
        text = str(getattr(webrtc_data, "textbox", "") or "").strip()
        if not text:
            self._last_webrtc_submit_key = None
            return False

        webrtc_id = str(getattr(webrtc_data, "webrtc_id", "") or "")
        submit_key = (webrtc_id, text)
        if submit_key == self._last_webrtc_submit_key:
            return False
        self._last_webrtc_submit_key = submit_key

        self.chatbot.append({"role": "user", "content": text})
        reply = await self.send_text(text)
        if reply:
            self.chatbot.append({"role": "assistant", "content": reply})
        return True

    async def _sync_chatbot(self) -> None:
        if self.chatbot:
            return
        if not self.args_set.is_set():
            # Args are populated asynchronously by FastRTC tick handlers.
            # Do not block emit() when no args have arrived yet; otherwise
            # audio/text output queues cannot be drained and live responses
            # appear stalled.
            return
        history = self._extract_chat_history_from_args()
        if history is not None:
            self.chatbot = history

    async def _drain_text_queue(self) -> bool:
        updated = False
        while True:
            try:
                chunk = self.text_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if chunk == "<END_OF_RESPONSE>":
                self.assistant_active = False
                continue
            if not self.assistant_active:
                self.chatbot.append({"role": "assistant", "content": ""})
                self.assistant_active = True
            self.chatbot[-1]["content"] += str(chunk)
            updated = True
        return updated

    async def emit(self) -> Any:
        try:
            await self._ensure_ready()
            if self._audio_buffer_samples > 0:
                should_force_flush = (time.time() - self._last_audio_input_at) >= self._flush_idle_seconds
                await self._flush_audio_buffer(force=should_force_flush)
            await self._sync_chatbot()

            textbox_updated = await self._consume_webrtc_textbox_submission()
            text_updated = await self._drain_text_queue() or textbox_updated
            try:
                sample_rate, audio = self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                sample_rate, audio = None, None

            if audio is not None:
                if text_updated:
                    return (int(sample_rate), audio), AdditionalOutputs(self.chatbot)
                return int(sample_rate), audio
            if text_updated:
                return AdditionalOutputs(self.chatbot)
            return None
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._publish_runtime_error(e)
            try:
                await self._sync_chatbot()
                if await self._drain_text_queue():
                    return AdditionalOutputs(self.chatbot)
            except Exception:
                pass
            logger.debug("MiniCPM emit failed: %s", e)
            return None

    async def video_emit(self) -> Any:
        if self._latest_video_frame is not None:
            return self._latest_video_frame
        return np.zeros((240, 320, 3), dtype=np.uint8)

    async def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        if MiniCPMOmniRealtimeHandler._active_instance is self:
            MiniCPMOmniRealtimeHandler._active_instance = None
        if self._video_prefill_task and not self._video_prefill_task.done():
            self._video_prefill_task.cancel()
            try:
                await self._video_prefill_task
            except BaseException:
                pass
        if self._generate_task and not self._generate_task.done():
            self._generate_task.cancel()
            try:
                await self._generate_task
            except BaseException:
                pass
        await self.client.close()
