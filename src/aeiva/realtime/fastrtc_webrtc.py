from __future__ import annotations

import logging
from typing import Any, TypeVar, cast


logger = logging.getLogger(__name__)

TWebRTC = TypeVar("TWebRTC")


def build_safe_webrtc_component(base_webrtc_cls: type[TWebRTC]) -> type[TWebRTC]:
    """
    Patch a WebRTC class in place with stale-submit safety.

    FastRTC may dispatch a late submit event after a connection has been cleaned
    up. Upstream behavior indexes `self.handlers[webrtc_id]` directly, which can
    raise KeyError and break UI interactions. We patch the original component
    class rather than subclassing it so Gradio still resolves the correct
    frontend asset bundle for the custom component.
    """
    if getattr(base_webrtc_cls, "_aeiva_safe_submit_patched", False):
        return cast(type[TWebRTC], base_webrtc_cls)

    def _safe_set_input_on_submit(self: Any, webrtc_data: Any, *args: Any) -> None:
        webrtc_id = webrtc_data
        if hasattr(webrtc_data, "webrtc_id"):
            webrtc_id = webrtc_data.webrtc_id
        key = cast(str, webrtc_id)
        self.set_input(key, webrtc_data, *args)
        handler = self.handlers.get(key)
        if handler is None:
            logger.debug("Ignored stale WebRTC submit event (webrtc_id=%s)", key)
            return
        if hasattr(handler, "trigger_response"):
            handler.trigger_response()  # type: ignore[attr-defined]

    setattr(base_webrtc_cls, "set_input_on_submit", _safe_set_input_on_submit)
    setattr(base_webrtc_cls, "_aeiva_safe_submit_patched", True)
    return cast(type[TWebRTC], base_webrtc_cls)
