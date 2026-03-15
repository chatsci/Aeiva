from __future__ import annotations

import logging
from typing import Any, TypeVar, cast


logger = logging.getLogger(__name__)

TWebRTC = TypeVar("TWebRTC")


def build_safe_webrtc_component(base_webrtc_cls: type[TWebRTC]) -> type[TWebRTC]:
    """
    Return a WebRTC subclass with stale-submit safety.

    FastRTC may dispatch a late submit event after a connection has been cleaned
    up. Upstream behavior indexes `self.handlers[webrtc_id]` directly, which can
    raise KeyError and break UI interactions. This wrapper keeps behavior aligned
    but ignores stale ids safely.
    """
from gradio.events import Dependency

    class AeivaWebRTC(base_webrtc_cls):  # type: ignore[misc, valid-type]
        def set_input_on_submit(self, webrtc_data: Any, *args: Any) -> None:
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

    AeivaWebRTC.__name__ = f"AeivaSafe{getattr(base_webrtc_cls, '__name__', 'WebRTC')}"
    return cast(type[TWebRTC], AeivaWebRTC)
