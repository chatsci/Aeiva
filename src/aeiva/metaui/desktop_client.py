from __future__ import annotations

import argparse
import sys
from typing import Optional

from .desktop_template import render_desktop_html


def run_desktop_client(*, ws_url: str, token: Optional[str] = None) -> int:
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWidgets import QApplication
    except Exception as exc:
        raise RuntimeError(
            "PySide6 + QtWebEngine are required for MetaUI desktop. "
            "Install with: pip install PySide6"
        ) from exc

    app = QApplication(sys.argv)
    view = QWebEngineView()
    view.setWindowTitle("AEIVA MetaUI Desktop")
    view.resize(1280, 820)
    view.setHtml(render_desktop_html(ws_url=ws_url, token=token), QUrl("http://metaui.local/"))
    view.show()
    return int(app.exec())


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MetaUI desktop client.")
    parser.add_argument("--ws-url", required=True, help="MetaUI orchestrator websocket URL.")
    parser.add_argument("--token", default="", help="Optional auth token.")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    return run_desktop_client(ws_url=args.ws_url, token=args.token)


if __name__ == "__main__":
    raise SystemExit(main())
