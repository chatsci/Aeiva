from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Optional

_TEMPLATE_RESOURCE = files("aeiva.metaui.assets").joinpath("desktop_template.html")
_CSS_RESOURCE = files("aeiva.metaui.assets").joinpath("desktop_styles.css")
_JS_PARTS_DIR = files("aeiva.metaui.assets").joinpath("desktop_js")
_REQUIRED_PLACEHOLDERS = ("__METAUI_CSS__", "__METAUI_JS__")


@lru_cache(maxsize=1)
def _load_template() -> str:
    template = _TEMPLATE_RESOURCE.read_text(encoding="utf-8")
    missing = [placeholder for placeholder in _REQUIRED_PLACEHOLDERS if placeholder not in template]
    if missing:
        raise RuntimeError(f"MetaUI desktop template missing placeholders: {missing}")
    css = _CSS_RESOURCE.read_text(encoding="utf-8").strip("\n")
    js = _load_js_source()
    return template.replace("__METAUI_CSS__", css).replace("__METAUI_JS__", js)


def _load_js_source() -> str:
    # Split modules are the canonical source for desktop JS runtime.
    try:
        part_names = sorted(
            item.name
            for item in _JS_PARTS_DIR.iterdir()
            if item.is_file() and item.name.endswith(".js")
        )
    except Exception:
        part_names = []
    if part_names:
        chunks = [
            _JS_PARTS_DIR.joinpath(name).read_text(encoding="utf-8").strip("\n")
            for name in part_names
        ]
        return "\n".join(chunks)
    raise RuntimeError("MetaUI desktop JS modules are missing from assets/desktop_js.")


HTML_TEMPLATE = _load_template()


def render_desktop_html(ws_url: str, token: Optional[str]) -> str:
    return (
        HTML_TEMPLATE
        .replace("__WS_URL__", json.dumps(ws_url))
        .replace("__TOKEN__", json.dumps(token or ""))
    )
