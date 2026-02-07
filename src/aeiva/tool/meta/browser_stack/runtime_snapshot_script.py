"""DOM snapshot script for browser runtime."""

_SNAPSHOT_JS = """
({ limit }) => {
  const maxItems = Math.max(1, Math.min(Number(limit || 80), 200));
  const refAttr = "data-aeiva-ref";
  if (!Number.isInteger(window.__aeivaRefCounter) || window.__aeivaRefCounter < 1) {
    window.__aeivaRefCounter = 1;
  }

  const candidates = Array.from(
    document.querySelectorAll(
      "input,textarea,select,button,a,summary,[role],[onclick],[tabindex],[contenteditable='true']"
    )
  );

  const esc = (value) => {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(String(value));
    }
    return String(value).replace(/([ #;?%&,.+*~':!^$[\\]()=>|\\/])/g, "\\\\$1");
  };

  const visible = (el) => {
    if (!(el instanceof HTMLElement)) return false;
    const style = window.getComputedStyle(el);
    if (!style || style.display === "none" || style.visibility === "hidden") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const roleOf = (el) => {
    const explicitRole = el.getAttribute("role");
    if (explicitRole) return explicitRole;
    return el.tagName.toLowerCase();
  };

  const priorityOf = (el) => {
    const tag = el.tagName.toLowerCase();
    const role = (el.getAttribute("role") || "").toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();

    if (tag === "input" || tag === "textarea" || tag === "select") return 100;
    if (role === "combobox" || role === "listbox" || role === "option") return 95;
    if (role === "textbox" || role === "searchbox" || role === "spinbutton") return 92;
    if (type === "date" || type === "datetime-local" || type === "time") return 90;
    if (tag === "button" || role === "button") return 80;
    if (tag === "a") return 70;
    if (el.hasAttribute("tabindex")) return 60;
    return 50;
  };

  const norm = (value, max = 160) =>
    String(value || "").replace(/\\s+/g, " ").trim().slice(0, max);

  const labelTextOf = (el) => {
    const labels = [];
    const pushLabel = (value) => {
      const clean = norm(value, 200);
      if (clean) labels.push(clean);
    };

    try {
      if ("labels" in el && el.labels) {
        for (const labelEl of Array.from(el.labels)) {
          pushLabel(labelEl && labelEl.textContent);
        }
      }
    } catch (_) {}

    const id = norm(el.id || "", 120);
    if (id) {
      const byFor = document.querySelector(`label[for="${esc(id)}"]`);
      if (byFor) {
        pushLabel(byFor.textContent);
      }
    }

    const parentLabel = typeof el.closest === "function" ? el.closest("label") : null;
    if (parentLabel) {
      pushLabel(parentLabel.textContent);
    }

    const labelledBy = norm(el.getAttribute("aria-labelledby") || "", 400);
    if (labelledBy) {
      for (const token of labelledBy.split(/\\s+/)) {
        if (!token) continue;
        const target = document.getElementById(token);
        if (target) {
          pushLabel(target.textContent);
        }
      }
    }

    return Array.from(new Set(labels)).join(" ").slice(0, 200);
  };

  const textOf = (el) => {
    const ariaLabel = el.getAttribute("aria-label") || "";
    const title = el.getAttribute("title") || "";
    const labelText = labelTextOf(el);
    const nameAttr = el.getAttribute("name") || "";
    const placeholder = el.getAttribute("placeholder") || "";
    const text = el.textContent || "";
    const value = "value" in el ? el.value : "";
    return norm(ariaLabel || title || labelText || nameAttr || placeholder || text || value);
  };

  const selectorOf = (el) => {
    if (el.id) return `#${esc(el.id)}`;

    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === Node.ELEMENT_NODE && parts.length < 6) {
      let part = cur.tagName.toLowerCase();

      const classes = Array.from(cur.classList || []).filter(Boolean);
      if (classes.length > 0) {
        part += `.${esc(classes[0])}`;
      }

      if (cur.parentElement) {
        const sameTag = Array.from(cur.parentElement.children).filter(
          (node) => node.tagName === cur.tagName
        );
        if (sameTag.length > 1) {
          part += `:nth-of-type(${sameTag.indexOf(cur) + 1})`;
        }
      }

      parts.unshift(part);
      cur = cur.parentElement;
      if (!cur || cur.tagName.toLowerCase() === "html") break;
    }
    return parts.join(" > ");
  };

  const ensureRef = (el) => {
    const existing = (el.getAttribute(refAttr) || "").trim();
    if (existing) return existing;

    let value = "";
    for (let i = 0; i < 20000; i++) {
      const candidate = `e${window.__aeivaRefCounter++}`;
      const owner = document.querySelector(`[${refAttr}="${candidate}"]`);
      if (!owner || owner === el) {
        value = candidate;
        break;
      }
    }
    if (!value) {
      value = `e${Date.now()}`;
    }
    el.setAttribute(refAttr, value);
    return value;
  };

  const seen = new Set();
  candidates.sort((a, b) => priorityOf(b) - priorityOf(a));
  const out = [];
  for (const el of candidates) {
    if (!visible(el)) continue;
    const fallbackSelector = selectorOf(el);
    const ref = ensureRef(el);
    const stableSelector = `[${refAttr}="${ref}"]`;

    if ((!stableSelector && !fallbackSelector) || seen.has(ref)) continue;
    seen.add(ref);
    const labelText = labelTextOf(el);
    const nameAttr = norm(el.getAttribute("name") || "", 120);
    out.push({
      ref,
      tag: el.tagName.toLowerCase(),
      role: roleOf(el),
      name: textOf(el),
      text: norm(el.textContent || "", 160),
      aria_label: norm(el.getAttribute("aria-label") || "", 160),
      placeholder: norm(el.getAttribute("placeholder") || "", 160),
      value: "value" in el ? norm(el.value || "", 160) : "",
      aria_valuenow: norm(el.getAttribute("aria-valuenow") || "", 80),
      input_type: String(el.getAttribute("type") || "").toLowerCase(),
      dom_id: norm(el.id || "", 120),
      name_attr: nameAttr,
      label_text: labelText,
      readonly: Boolean(el.readOnly === true || el.hasAttribute("readonly")),
      disabled: Boolean(el.disabled === true || el.hasAttribute("disabled")),
      selector: stableSelector,
      fallback_selector: fallbackSelector
    });
    if (out.length >= maxItems) break;
  }
  return out;
}
"""
