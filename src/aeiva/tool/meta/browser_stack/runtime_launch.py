"""Launch strategy mixin for PlaywrightRuntime."""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any, Dict, List, Optional

from .runtime_common import _parse_bool_env


class RuntimeLaunchMixin:
    async def _launch_browser_with_fallback(self, playwright: Any) -> tuple[Any, str]:
        browser_type = playwright.chromium
        common_args = [
            "--disable-dev-shm-usage",
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        requested_headless = bool(self.headless)
        prefer_installed = _parse_bool_env("AEIVA_BROWSER_PREFER_INSTALLED", True)

        env_executable = os.getenv("AEIVA_BROWSER_EXECUTABLE_PATH", "").strip() or None
        env_channels_raw = os.getenv("AEIVA_BROWSER_CHANNELS", "").strip()
        env_channels = [
            item.strip()
            for item in env_channels_raw.split(",")
            if item.strip()
        ]
        preferred_channels = env_channels or ["chrome", "msedge"]
        preferred_executables: List[Dict[str, str]] = []
        if env_executable:
            preferred_executables.append({"label": "env", "path": env_executable})
        preferred_executables.extend(self._discover_browser_executables())
        candidates = self._build_launch_candidates(
            requested_headless=requested_headless,
            preferred_channels=preferred_channels,
            preferred_executables=preferred_executables,
            common_args=common_args,
            prefer_installed=prefer_installed,
        )

        failures: List[str] = []
        seen_signatures: set[str] = set()

        for entry in candidates:
            kwargs = entry["kwargs"]
            signature = repr(sorted(kwargs.items()))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            label = entry["label"]
            try:
                browser = await browser_type.launch(**kwargs)
                return browser, label
            except Exception as exc:
                message = self._compact_exception_message(exc)
                failures.append(f"{label}: {message}")

        guidance = [
            "Failed to launch browser automation.",
            "Set `AEIVA_BROWSER_CHANNELS=chrome` or `AEIVA_BROWSER_EXECUTABLE_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` and retry.",
        ]
        if failures:
            guidance.append("Attempts: " + " | ".join(failures[:5]))
        raise RuntimeError(" ".join(guidance))

    @staticmethod
    def _build_launch_candidates(
        *,
        requested_headless: bool,
        preferred_channels: List[str],
        preferred_executables: List[Dict[str, str]],
        common_args: List[str],
        prefer_installed: bool,
    ) -> List[Dict[str, Any]]:
        channels: List[str] = []
        seen_channels: set[str] = set()
        for channel in preferred_channels:
            normalized = str(channel).strip().lower()
            if not normalized or normalized in seen_channels:
                continue
            seen_channels.add(normalized)
            channels.append(normalized)

        executables: List[Dict[str, str]] = []
        seen_paths: set[str] = set()
        for item in preferred_executables:
            raw_path = str(item.get("path") or "").strip()
            if not raw_path:
                continue
            expanded_path = os.path.expanduser(raw_path)
            normalized_path = os.path.realpath(expanded_path)
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)
            label = str(item.get("label") or "auto").strip() or "auto"
            executables.append({"label": label, "path": expanded_path})

        def with_suffix(base: str, headless: bool) -> str:
            if headless == requested_headless:
                return base
            return f"{base}-headed-fallback"

        def candidate(
            label: str,
            *,
            headless: bool,
            channel: Optional[str] = None,
            executable_path: Optional[str] = None,
        ) -> Dict[str, Any]:
            launch_kwargs: Dict[str, Any] = {
                "headless": headless,
                "args": list(common_args),
                "chromium_sandbox": False,
            }
            if channel:
                launch_kwargs["channel"] = channel
            if executable_path:
                launch_kwargs["executable_path"] = executable_path
            return {"label": label, "kwargs": launch_kwargs}

        def preferred_order(headless: bool) -> List[Dict[str, Any]]:
            ordered: List[Dict[str, Any]] = []
            for executable in executables:
                ordered.append(
                    candidate(
                        with_suffix(f"chromium-executable:{executable['label']}", headless),
                        headless=headless,
                        executable_path=executable["path"],
                    )
                )
            for channel in channels:
                ordered.append(
                    candidate(
                        with_suffix(f"chromium-channel:{channel}", headless),
                        headless=headless,
                        channel=channel,
                    )
                )
            ordered.append(candidate(with_suffix("chromium-default", headless), headless=headless))
            return ordered

        def chromium_first_order(headless: bool) -> List[Dict[str, Any]]:
            ordered: List[Dict[str, Any]] = []
            ordered.append(candidate(with_suffix("chromium-default", headless), headless=headless))
            for channel in channels:
                ordered.append(
                    candidate(
                        with_suffix(f"chromium-channel:{channel}", headless),
                        headless=headless,
                        channel=channel,
                    )
                )
            for executable in executables:
                ordered.append(
                    candidate(
                        with_suffix(f"chromium-executable:{executable['label']}", headless),
                        headless=headless,
                        executable_path=executable["path"],
                    )
                )
            return ordered

        candidates = (
            preferred_order(requested_headless)
            if prefer_installed
            else chromium_first_order(requested_headless)
        )
        if requested_headless:
            headed = preferred_order(False) if prefer_installed else chromium_first_order(False)
            candidates.extend(headed)
        return candidates

    @staticmethod
    def _discover_browser_executables() -> List[Dict[str, str]]:
        discovered: List[Dict[str, str]] = []
        seen_paths: set[str] = set()

        def add(label: str, path: Optional[str]) -> None:
            if not path:
                return
            expanded = os.path.expanduser(str(path).strip())
            if not expanded or not os.path.isabs(expanded):
                return
            if not os.path.isfile(expanded):
                return
            normalized = os.path.realpath(expanded)
            if normalized in seen_paths:
                return
            seen_paths.add(normalized)
            discovered.append({"label": label, "path": expanded})

        if sys.platform == "darwin":
            home = os.path.expanduser("~")
            mac_paths = [
                ("mac:chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                (
                    "mac:chrome-beta",
                    "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta",
                ),
                ("mac:chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
                ("mac:edge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                (
                    "mac:user-chrome",
                    f"{home}/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                ),
                ("mac:user-chromium", f"{home}/Applications/Chromium.app/Contents/MacOS/Chromium"),
                (
                    "mac:user-edge",
                    f"{home}/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                ),
            ]
            for label, path in mac_paths:
                add(label, path)
        elif sys.platform.startswith("win"):
            program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            windows_paths = [
                ("win:chrome", fr"{program_files}\Google\Chrome\Application\chrome.exe"),
                ("win:chrome-x86", fr"{program_files_x86}\Google\Chrome\Application\chrome.exe"),
                ("win:edge", fr"{program_files}\Microsoft\Edge\Application\msedge.exe"),
                ("win:edge-x86", fr"{program_files_x86}\Microsoft\Edge\Application\msedge.exe"),
                ("win:chromium", fr"{program_files}\Chromium\Application\chrome.exe"),
            ]
            if local_app_data:
                windows_paths.extend(
                    [
                        ("win:user-chrome", fr"{local_app_data}\Google\Chrome\Application\chrome.exe"),
                        ("win:user-edge", fr"{local_app_data}\Microsoft\Edge\Application\msedge.exe"),
                    ]
                )
            for label, path in windows_paths:
                add(label, path)
        else:
            linux_paths = [
                ("linux:chrome", "/usr/bin/google-chrome"),
                ("linux:chrome-stable", "/usr/bin/google-chrome-stable"),
                ("linux:chromium", "/usr/bin/chromium"),
                ("linux:chromium-browser", "/usr/bin/chromium-browser"),
                ("linux:edge", "/usr/bin/microsoft-edge"),
                ("linux:edge-stable", "/usr/bin/microsoft-edge-stable"),
                ("linux:msedge", "/usr/bin/msedge"),
            ]
            for label, path in linux_paths:
                add(label, path)

        which_names = [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
            "microsoft-edge-stable",
            "msedge",
        ]
        for name in which_names:
            add(f"which:{name}", shutil.which(name))

        return discovered

    @staticmethod
    def _compact_exception_message(exc: Exception) -> str:
        text = str(exc).strip()
        if not text:
            return exc.__class__.__name__
        lowered = text.lower()
        if "mach_port_rendezvous" in lowered:
            return "macOS launch permission error (mach_port_rendezvous)"
        if "no such file or directory" in lowered:
            return "executable not found"
        if "failed to launch" in lowered:
            return "failed to launch"
        if len(text) > 220:
            return text[:220] + "..."
        return text
