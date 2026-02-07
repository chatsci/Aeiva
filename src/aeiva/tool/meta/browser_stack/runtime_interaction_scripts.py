"""Shared JS snippets used by runtime interaction helpers."""

NUMERIC_VALUE_FALLBACK_JS = """(el, args) => {
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
}"""
