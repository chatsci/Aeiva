"""Interaction helper mixin for PlaywrightRuntime."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .runtime_common import (
    DEFAULT_SELECT_SETTLE_MS,
    DEFAULT_SLOW_TYPE_DELAY_MS,
    DEFAULT_TYPE_DELAY_MS,
    _distributed_attempt_timeout,
    _extract_numeric_token,
    _normalize_text_value,
    _normalize_timeout,
    _parse_int_env,
    _safe_title,
)


class RuntimeInteractionMixin:
    def _resolve_selector(
        self,
        *,
        target_id: str,
        selector: Optional[str],
        ref: Optional[str],
    ) -> tuple[str, Optional[str]]:
        clean_ref = (ref or "").strip()
        clean_selector = (selector or "").strip()

        if clean_ref:
            tab = self._tab_states.get(target_id)
            if tab:
                entry = tab.refs.get(clean_ref)
                if isinstance(entry, str) and entry.strip():
                    return entry.strip(), None
                if isinstance(entry, dict):
                    primary = _safe_title(entry.get("selector")).strip()
                    fallback = _safe_title(entry.get("fallback_selector")).strip()
                    if primary:
                        return primary, (fallback or None)
                    if fallback:
                        return fallback, None
            raise ValueError(
                f"Unknown ref: {clean_ref}. Call snapshot first and use returned refs."
            )

        if clean_selector:
            return clean_selector, None

        raise ValueError("selector or ref is required")

    async def _wait_for_locator(
        self,
        page: Any,
        selector: str,
        timeout_ms: int,
        *,
        fallback_selector: Optional[str] = None,
        allow_attached_fallback: bool = False,
    ) -> Any:
        timeout_value = _normalize_timeout(timeout_ms)
        selectors = [selector]
        if fallback_selector and fallback_selector != selector:
            selectors.append(fallback_selector)

        contexts = self._iter_locator_contexts(page)
        deadline = time.monotonic() + (timeout_value / 1000.0)
        attempt_timeout = max(
            120,
            min(
                1200,
                timeout_value // max(1, len(contexts) * len(selectors)),
            ),
        )
        last_error: Optional[Exception] = None
        for candidate in selectors:
            for context in contexts:
                locator = context.locator(candidate).first
                remaining_ms = int((deadline - time.monotonic()) * 1000)
                if remaining_ms <= 0:
                    break
                timeout_for_attempt = max(60, min(attempt_timeout, remaining_ms))
                try:
                    await locator.wait_for(state="visible", timeout=timeout_for_attempt)
                    return locator
                except Exception as exc:
                    last_error = exc
            if int((deadline - time.monotonic()) * 1000) <= 0:
                break

        if allow_attached_fallback:
            for candidate in selectors:
                for context in contexts:
                    locator = context.locator(candidate).first
                    remaining_ms = int((deadline - time.monotonic()) * 1000)
                    if remaining_ms <= 0:
                        break
                    timeout_for_attempt = max(60, min(attempt_timeout, remaining_ms))
                    try:
                        await locator.wait_for(state="attached", timeout=timeout_for_attempt)
                        return locator
                    except Exception as exc:
                        last_error = exc
                if int((deadline - time.monotonic()) * 1000) <= 0:
                    break

        if last_error is not None:
            raise last_error
        raise ValueError("Unable to resolve locator")

    def _iter_locator_contexts(self, page: Any) -> List[Any]:
        contexts: List[Any] = [page]
        seen: set[int] = {id(page)}
        main_frame = getattr(page, "main_frame", None)
        frames = getattr(page, "frames", None) or []
        for frame in frames:
            if frame is None:
                continue
            if main_frame is not None and frame is main_frame:
                continue
            marker = id(frame)
            if marker in seen:
                continue
            seen.add(marker)
            contexts.append(frame)
        return contexts

    async def _type_via_keyboard(
        self,
        page: Any,
        locator: Optional[Any],
        text: str,
        timeout_ms: int,
        *,
        slowly: bool,
    ) -> None:
        if locator is not None:
            await locator.click(timeout=timeout_ms)
        for chord in ("Meta+A", "Control+A"):
            try:
                await page.keyboard.press(chord, timeout=timeout_ms)
                break
            except Exception:
                continue
        try:
            await page.keyboard.press("Backspace", timeout=timeout_ms)
        except Exception:
            pass
        if slowly:
            delay = _parse_int_env(
                "AEIVA_BROWSER_SLOW_TYPE_DELAY_MS",
                DEFAULT_SLOW_TYPE_DELAY_MS,
                0,
            )
        else:
            delay = _parse_int_env(
                "AEIVA_BROWSER_TYPE_DELAY_MS",
                DEFAULT_TYPE_DELAY_MS,
                0,
            )
        await page.keyboard.type(text, delay=max(0, int(delay)))

    async def _apply_numeric_value_fallback(
        self,
        *,
        locator: Any,
        text: str,
        timeout_ms: int,
    ) -> bool:
        target = _extract_numeric_token(text)
        if target is None:
            return False

        try:
            result = await locator.evaluate(
                """(el, args) => {
                  const parseNumber = (value) => {
                    const normalized = String(value ?? "").replace(/,/g, ".");
                    const match = normalized.match(/-?\\d+(?:\\.\\d+)?/);
                    if (!match) return null;
                    const parsed = Number(match[0]);
                    return Number.isFinite(parsed) ? parsed : null;
                  };
                  const target = Number.isFinite(Number(args?.target_value))
                    ? Number(args.target_value)
                    : parseNumber(args?.raw_text);
                  if (target === null) {
                    return { applied: false, reason: "not_numeric" };
                  }

                  const readNumeric = (node) => {
                    if (!node) return null;
                    if ("value" in node) {
                      const parsed = parseNumber(node.value);
                      if (parsed !== null) return parsed;
                    }
                    if (typeof node.getAttribute === "function") {
                      const ariaValue = parseNumber(node.getAttribute("aria-valuenow"));
                      if (ariaValue !== null) return ariaValue;
                    }
                    if (typeof node.querySelector === "function") {
                      const nested = node.querySelector("[role='spinbutton'], input, textarea");
                      if (nested) return readNumeric(nested);
                    }
                    return null;
                  };

                  const emitInputEvents = (node) => {
                    node.dispatchEvent(new Event("input", { bubbles: true }));
                    node.dispatchEvent(new Event("change", { bubbles: true }));
                  };

                  const near = (a, b) =>
                    a !== null && b !== null && Math.abs(Number(a) - Number(b)) < 1e-4;

                  let control = el;
                  if (control && typeof control.querySelector === "function") {
                    const nested = control.querySelector("[role='spinbutton'], input, textarea");
                    if (nested) control = nested;
                  }
                  if (!control) return { applied: false, reason: "missing_control" };
                  if (control instanceof HTMLElement) {
                    try { control.focus(); } catch {}
                  }

                  let current = readNumeric(control);

                  if ("value" in control && !control.disabled) {
                    try {
                      control.value = String(target);
                      emitInputEvents(control);
                      current = readNumeric(control);
                      if (near(current, target)) {
                        return {
                          applied: true,
                          strategy: "value",
                          value: String(control.value ?? ""),
                          current
                        };
                      }
                    } catch {}
                  }

                  if (current !== null && (typeof control.stepUp === "function" || typeof control.stepDown === "function")) {
                    let guard = 0;
                    while (!near(current, target) && guard < 40) {
                      if (current < target && typeof control.stepUp === "function") {
                        control.stepUp();
                      } else if (current > target && typeof control.stepDown === "function") {
                        control.stepDown();
                      } else {
                        break;
                      }
                      emitInputEvents(control);
                      current = readNumeric(control);
                      guard += 1;
                    }
                    if (near(current, target)) {
                      return {
                        applied: true,
                        strategy: "step",
                        value: String("value" in control ? control.value ?? "" : current ?? ""),
                        current
                      };
                    }
                  }

                  if (current !== null) {
                    const container =
                      (typeof control.closest === "function" && control.closest("[role], form, section, div")) ||
                      control.parentElement;
                    if (container && typeof container.querySelectorAll === "function") {
                      const scoreButton = (node) => {
                        const label = String(
                          node.getAttribute?.("aria-label") ||
                          node.getAttribute?.("title") ||
                          node.textContent ||
                          ""
                        ).toLowerCase();
                        if (!label) return 0;
                        if (/[+＋]/.test(label) || /(add|increase|increment|more|up|加|增加|上)/.test(label)) return 1;
                        if (/[-−]/.test(label) || /(minus|decrease|decrement|less|down|减|减少|下)/.test(label)) return -1;
                        return 0;
                      };
                      const buttons = Array.from(container.querySelectorAll("button, [role='button']"));
                      const plus = buttons.find((node) => scoreButton(node) > 0) || null;
                      const minus = buttons.find((node) => scoreButton(node) < 0) || null;
                      let guard = 0;
                      while (!near(current, target) && guard < 40) {
                        const btn = current < target ? plus : minus;
                        if (!btn) break;
                        if (btn instanceof HTMLElement) {
                          try { btn.click(); } catch {}
                        }
                        current = readNumeric(control);
                        guard += 1;
                      }
                      if (near(current, target)) {
                        return {
                          applied: true,
                          strategy: "buttons",
                          value: String("value" in control ? control.value ?? "" : current ?? ""),
                          current
                        };
                      }
                    }
                  }

                  return {
                    applied: near(current, target),
                    strategy: "none",
                    current,
                    target
                  };
                }""",
                {
                    "raw_text": text,
                    "target_value": target,
                    "timeout_ms": int(timeout_ms),
                },
            )
        except Exception:
            return False

        if not isinstance(result, dict):
            return False
        return bool(result.get("applied"))

    async def _select_custom_values(
        self,
        *,
        page: Any,
        control_locator: Any,
        values: List[str],
        timeout_ms: int,
    ) -> None:
        for index, value in enumerate(values):
            await control_locator.click(timeout=timeout_ms)
            selected = await self._pick_option_from_contexts(
                page=page,
                value=str(value),
                timeout_ms=timeout_ms,
            )
            if not selected:
                selected = await self._select_value_via_typed_input(
                    page=page,
                    value=str(value),
                    timeout_ms=timeout_ms,
                    control_locator=control_locator,
                )
            if not selected:
                selected = await self._apply_numeric_value_fallback(
                    locator=control_locator,
                    text=str(value),
                    timeout_ms=timeout_ms,
                )
            if not selected:
                raise ValueError(f"Unable to select option: {value}")
            if index + 1 < len(values):
                # Some custom multi-select controls need a short settle before reopen.
                try:
                    await page.wait_for_timeout(80)
                except Exception:
                    pass

    async def _select_values_from_open_dropdown(
        self,
        *,
        page: Any,
        values: List[str],
        timeout_ms: int,
    ) -> None:
        for value in values:
            selected = await self._pick_option_from_contexts(
                page=page,
                value=str(value),
                timeout_ms=timeout_ms,
            )
            if not selected:
                selected = await self._select_value_via_typed_input(
                    page=page,
                    value=str(value),
                    timeout_ms=timeout_ms,
                    control_locator=None,
                )
            if not selected:
                raise ValueError(
                    f"Unable to select option: {value}. Provide selector/ref for the control."
                )

    async def _select_value_via_typed_input(
        self,
        *,
        page: Any,
        value: str,
        timeout_ms: int,
        control_locator: Optional[Any],
    ) -> bool:
        editable: Optional[Any] = None
        if control_locator is not None:
            editable = await self._find_editable_within_locator(control_locator, timeout_ms)
        if editable is None and control_locator is None:
            editable = await self._find_best_editable_locator(page, timeout_ms)
        if editable is None:
            return False

        typed_ok, typed_locator = await self._write_text_with_fallback(
            page=page,
            locator=editable,
            text=value,
            timeout_ms=timeout_ms,
            slowly=False,
        )
        settle_ms = min(
            timeout_ms,
            _parse_int_env(
                "AEIVA_BROWSER_SELECT_SETTLE_MS",
                DEFAULT_SELECT_SETTLE_MS,
                40,
            ),
        )
        option_timeout = min(timeout_ms, 1200)
        for pre_enter_key in ("", "ArrowDown"):
            if pre_enter_key:
                try:
                    await page.keyboard.press(pre_enter_key, timeout=timeout_ms)
                except Exception:
                    pass
            try:
                await page.keyboard.press("Enter", timeout=timeout_ms)
            except Exception:
                pass
            try:
                await page.wait_for_timeout(max(0, int(settle_ms)))
            except Exception:
                pass
            picked = await self._pick_option_from_contexts(
                page=page,
                value=value,
                timeout_ms=option_timeout,
            )
            if picked:
                return True
            if typed_locator is not None and await self._text_matches_locator(typed_locator, value):
                return True
            if await self._text_matches_active(page, value):
                return True
        if not typed_ok:
            return False
        if typed_locator is not None and await self._text_matches_locator(typed_locator, value):
            return True
        return await self._text_matches_active(page, value)

    async def _focused_element_is_editable(self, page: Any) -> bool:
        try:
            result = await page.evaluate(
                """() => {
                  const el = document.activeElement;
                  if (!el) return false;
                  if (el instanceof HTMLInputElement) return !el.readOnly && !el.disabled;
                  if (el instanceof HTMLTextAreaElement) return !el.readOnly && !el.disabled;
                  if (el instanceof HTMLElement && el.isContentEditable) return true;
                  return false;
                }"""
            )
        except Exception:
            return False
        return bool(result)

    async def _find_best_editable_locator(
        self,
        page: Any,
        timeout_ms: int,
    ) -> Optional[Any]:
        contexts = self._iter_locator_contexts(page)
        selectors = (
            ":focus",
            "[role='combobox'] input:not([readonly]):not([disabled])",
            "input[role='combobox']:not([readonly]):not([disabled])",
            "input[aria-autocomplete]:not([readonly]):not([disabled])",
            "input:not([type='hidden']):not([readonly]):not([disabled])",
            "textarea:not([readonly]):not([disabled])",
            "[contenteditable='true']",
        )
        attempt_timeout = _distributed_attempt_timeout(
            timeout_ms,
            probe_count=len(contexts) * len(selectors),
            minimum=90,
            maximum=550,
        )

        for context in contexts:
            for selector in selectors:
                locator = context.locator(selector).first
                if not await self._locator_is_editable(locator, attempt_timeout):
                    continue
                try:
                    await locator.click(timeout=attempt_timeout)
                except Exception:
                    pass
                return locator
        return None

    async def _find_editable_within_locator(
        self,
        locator: Any,
        timeout_ms: int,
    ) -> Optional[Any]:
        selectors = (
            None,
            "[role='combobox'] input:not([readonly]):not([disabled])",
            "input:not([type='hidden']):not([readonly]):not([disabled])",
            "textarea:not([readonly]):not([disabled])",
            "[contenteditable='true']",
        )
        attempt_timeout = _distributed_attempt_timeout(
            timeout_ms,
            probe_count=len(selectors),
            minimum=90,
            maximum=550,
        )
        for selector in selectors:
            if selector is None:
                candidate = locator
            else:
                child_locator = getattr(locator, "locator", None)
                if not callable(child_locator):
                    continue
                candidate = child_locator(selector).first
            if not await self._locator_is_editable(candidate, attempt_timeout):
                continue
            try:
                await candidate.click(timeout=attempt_timeout)
            except Exception:
                pass
            return candidate
        return None

    async def _locator_is_editable(
        self,
        locator: Any,
        timeout_ms: int,
    ) -> bool:
        try:
            await locator.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            try:
                await locator.wait_for(state="attached", timeout=timeout_ms)
            except Exception:
                return False
        try:
            result = await locator.evaluate(
                """(el) => {
                  if (!el) return false;
                  if (el instanceof HTMLInputElement) return !el.readOnly && !el.disabled;
                  if (el instanceof HTMLTextAreaElement) return !el.readOnly && !el.disabled;
                  if (el instanceof HTMLElement && el.isContentEditable) return true;
                  const nested = el.querySelector(
                    "input:not([readonly]):not([disabled]), " +
                    "textarea:not([readonly]):not([disabled]), " +
                    "[contenteditable='true']"
                  );
                  if (!nested) return false;
                  if (nested instanceof HTMLInputElement || nested instanceof HTMLTextAreaElement) {
                    nested.focus();
                    return !nested.readOnly && !nested.disabled;
                  }
                  if (nested instanceof HTMLElement && nested.isContentEditable) {
                    nested.focus();
                    return true;
                  }
                  return false;
                }"""
            )
        except Exception:
            return True
        return bool(result)

    async def _read_field_value(
        self,
        *,
        page: Any,
        locator: Optional[Any],
    ) -> str:
        if locator is not None:
            value = await locator.evaluate(
                """(el) => {
                  const read = (node) => {
                    if (!node) return '';
                    if ('value' in node) return String(node.value ?? '');
                    if (node instanceof HTMLElement && node.isContentEditable) {
                      return String(node.textContent || '');
                    }
                    if (typeof node.getAttribute === 'function') {
                      const ariaValue = node.getAttribute('aria-valuenow');
                      if (ariaValue) return String(ariaValue);
                    }
                    if (typeof node.querySelector === 'function') {
                      const nested = node.querySelector("[role='spinbutton'], input, textarea");
                      if (nested) return read(nested);
                    }
                    return '';
                  };
                  return read(el);
                }"""
            )
            return str(value or "")
        value = await page.evaluate(
            """() => {
              const read = (node) => {
                if (!node) return '';
                if ('value' in node) return String(node.value ?? '');
                if (node instanceof HTMLElement && node.isContentEditable) {
                  return String(node.textContent || '');
                }
                if (typeof node.getAttribute === 'function') {
                  const ariaValue = node.getAttribute('aria-valuenow');
                  if (ariaValue) return String(ariaValue);
                }
                return '';
              };
              return read(document.activeElement);
            }"""
        )
        return str(value or "")

    async def _read_selected_values(
        self,
        *,
        page: Any,
        locator: Optional[Any],
    ) -> List[str]:
        if locator is not None:
            values = await locator.evaluate(
                """(el) => {
                  if (el && el.tagName && el.tagName.toLowerCase() === "select") {
                    return Array.from(el.selectedOptions || []).map(
                      (opt) => String(opt.value || opt.text || "")
                    );
                  }
                  if ('value' in el) return [String(el.value ?? "")];
                  return [];
                }"""
            )
        else:
            values = await page.evaluate(
                """() => {
                  const el = document.activeElement;
                  if (!el) return [];
                  if (el.tagName && el.tagName.toLowerCase() === 'select') {
                    return Array.from(el.selectedOptions || []).map(
                      (opt) => String(opt.value || opt.text || '')
                    );
                  }
                  if ('value' in el) return [String(el.value ?? '')];
                  return [];
                }"""
            )
        if not isinstance(values, list):
            return []
        out: List[str] = []
        for item in values:
            text = str(item).strip()
            if text:
                out.append(text)
        return out

    async def _text_matches_locator(self, locator: Any, expected_text: str) -> bool:
        expected = _normalize_text_value(expected_text)
        if not expected:
            return True
        try:
            payload = await locator.evaluate(
                """(el) => {
                  const read = (node) => {
                    if (!node) return '';
                    if ('value' in node) return String(node.value ?? '');
                    if (node instanceof HTMLElement && node.isContentEditable) {
                      return String(node.textContent || '');
                    }
                    if (typeof node.getAttribute === 'function') {
                      const ariaNow = node.getAttribute('aria-valuenow');
                      if (ariaNow) return String(ariaNow);
                    }
                    if (typeof node.querySelector === 'function') {
                      const nested = node.querySelector("[role='spinbutton'], input, textarea");
                      if (nested) return read(nested);
                    }
                    return '';
                  };
                  const hasNestedEditable = (() => {
                    if (!el || typeof el.querySelector !== 'function') return false;
                    const nested = el.querySelector(
                      "[role='spinbutton'], input, textarea, [contenteditable='true']"
                    );
                    return Boolean(nested && nested !== el);
                  })();
                  const isContentEditableHost = Boolean(
                    el instanceof HTMLElement && el.isContentEditable
                  );
                  const active = document.activeElement;
                  return {
                    own: read(el),
                    active: read(active),
                    text: String(el?.textContent || ''),
                    aria: String(el?.getAttribute?.('aria-label') || ''),
                    aria_value: String(el?.getAttribute?.('aria-valuenow') || ''),
                    is_contenteditable: isContentEditableHost,
                    has_nested_editable: hasNestedEditable,
                  };
                }"""
            )
        except Exception:
            return False

        candidates: List[str] = []
        include_text_candidate = False
        if isinstance(payload, dict):
            for key in ("own", "active", "text", "aria", "aria_value"):
                if key == "text":
                    continue
                if key == "aria":
                    continue
                value = payload.get(key)
                if isinstance(value, str) and value:
                    candidates.append(value)
            include_text_candidate = bool(payload.get("is_contenteditable")) and not bool(
                payload.get("has_nested_editable")
            )
            if include_text_candidate:
                text_value = payload.get("text")
                if isinstance(text_value, str) and text_value:
                    candidates.append(text_value)
        return any(self._text_matches_expected(candidate, expected) for candidate in candidates)

    async def _text_matches_active(self, page: Any, expected_text: str) -> bool:
        expected = _normalize_text_value(expected_text)
        if not expected:
            return True
        try:
            payload = await page.evaluate(
                """() => {
                  const el = document.activeElement;
                  if (!el) return { value: '', text: '' };
                  const value = 'value' in el ? String(el.value ?? '') : '';
                  const text = el instanceof HTMLElement ? String(el.textContent || '') : '';
                  return { value, text };
                }"""
            )
        except Exception:
            return False

        if isinstance(payload, dict):
            candidates = [payload.get("value"), payload.get("text")]
        else:
            candidates = [payload]
        return any(
            self._text_matches_expected(candidate, expected)
            for candidate in candidates
            if isinstance(candidate, str)
        )

    @staticmethod
    def _text_matches_expected(candidate: str, expected_normalized: str) -> bool:
        normalized = _normalize_text_value(candidate)
        if not normalized:
            return False
        expected = _normalize_text_value(expected_normalized)
        if not expected:
            return False
        candidate_numeric = _extract_numeric_token(normalized)
        expected_numeric = _extract_numeric_token(expected)
        if expected_numeric is not None:
            if candidate_numeric is None:
                return normalized == expected
            return abs(candidate_numeric - expected_numeric) < 1e-4
        return (
            normalized == expected
            or normalized.startswith(expected)
            or expected in normalized
        )

    async def _pick_option_from_contexts(
        self,
        *,
        page: Any,
        value: str,
        timeout_ms: int,
    ) -> bool:
        contexts = self._iter_locator_contexts(page)
        attempt_timeout = _distributed_attempt_timeout(
            timeout_ms,
            probe_count=len(contexts) * 7,
            minimum=120,
            maximum=700,
        )

        for context in contexts:
            locators: List[Any] = []
            for builder in (
                lambda: context.get_by_role("option", name=value, exact=True).first,
                lambda: context.get_by_role("option", name=value).first,
                lambda: context.get_by_text(value, exact=True).first,
                lambda: context.get_by_text(value).first,
                lambda: context.locator("option").filter(has_text=value).first,
                lambda: context.locator("[role='option']").filter(has_text=value).first,
                lambda: context.locator("[role='listbox'] [role='option']").filter(has_text=value).first,
            ):
                try:
                    locators.append(builder())
                except Exception:
                    continue

            for locator in locators:
                try:
                    await locator.wait_for(state="visible", timeout=attempt_timeout)
                    await locator.click(timeout=attempt_timeout)
                    return True
                except Exception:
                    continue
        return False

    @staticmethod
    def _normalize_selector_state(selector_state: Optional[str]) -> str:
        normalized = (selector_state or "").strip().lower()
        if normalized in {"visible", "hidden", "attached", "detached"}:
            return normalized
        return "visible"
