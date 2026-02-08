from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Optional

_TEMPLATE_RESOURCE = files("aeiva.metaui.assets").joinpath("desktop_template.html")
_REQUIRED_PLACEHOLDERS = ("__WS_URL__", "__TOKEN__")


@lru_cache(maxsize=1)
def _load_template() -> str:
    template = _TEMPLATE_RESOURCE.read_text(encoding="utf-8")
    missing = [placeholder for placeholder in _REQUIRED_PLACEHOLDERS if placeholder not in template]
    if missing:
        raise RuntimeError(f"MetaUI desktop template missing placeholders: {missing}")
    return template


HTML_TEMPLATE = _load_template()


def render_desktop_html(ws_url: str, token: Optional[str]) -> str:
    return (
        HTML_TEMPLATE
        .replace("__WS_URL__", json.dumps(ws_url))
        .replace("__TOKEN__", json.dumps(token or ""))
    )
