"""Shared JS snippets for runtime scrolling operations."""

ELEMENT_SCROLL_JS = """(el, delta) => {
  const dx = Number(delta?.x || 0);
  const dy = Number(delta?.y || 0);
  const canScrollX = (el.scrollWidth || 0) > (el.clientWidth || 0);
  const canScrollY = (el.scrollHeight || 0) > (el.clientHeight || 0);
  if (!canScrollX && !canScrollY) {
    return {
      scrolled: false,
      left: Number(el.scrollLeft || 0),
      top: Number(el.scrollTop || 0)
    };
  }
  if (typeof el.scrollBy === "function") {
    el.scrollBy(dx, dy);
  } else {
    el.scrollLeft = Number(el.scrollLeft || 0) + dx;
    el.scrollTop = Number(el.scrollTop || 0) + dy;
  }
  return {
    scrolled: true,
    left: Number(el.scrollLeft || 0),
    top: Number(el.scrollTop || 0)
  };
}"""

ACTIVE_CONTAINER_SCROLL_JS = """(delta) => {
  const dx = Number(delta?.x || 0);
  const dy = Number(delta?.y || 0);

  const isVisible = (el) => {
    if (!(el instanceof HTMLElement)) return false;
    const style = window.getComputedStyle(el);
    if (!style) return false;
    if (style.display === "none" || style.visibility === "hidden") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const isScrollable = (el) => {
    if (!(el instanceof HTMLElement)) return false;
    const canX = (el.scrollWidth || 0) > (el.clientWidth || 0) + 1;
    const canY = (el.scrollHeight || 0) > (el.clientHeight || 0) + 1;
    return canX || canY;
  };

  const buildContainerKey = (el) => {
    if (!(el instanceof HTMLElement)) return "";
    const tag = String(el.tagName || "").toLowerCase();
    const id = String(el.id || "").trim();
    const classes = String(el.className || "")
      .trim()
      .split(/\\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .join(".");
    const role = String(el.getAttribute("role") || "").trim();
    const aria = String(el.getAttribute("aria-label") || "").trim().slice(0, 24);
    return [tag, id, classes, role, aria].filter(Boolean).join("|");
  };

  const collectAncestors = (node) => {
    const out = [];
    let cur = node;
    while (cur && cur instanceof HTMLElement && out.length < 16) {
      out.push(cur);
      cur = cur.parentElement;
    }
    return out;
  };

  const candidates = [];
  const active = document.activeElement;
  if (active instanceof HTMLElement) {
    candidates.push(...collectAncestors(active));
  }

  const overlays = Array.from(
    document.querySelectorAll(
      "[aria-modal='true'], [role='dialog'], [role='listbox'], [role='menu'], [role='region']"
    )
  );
  for (const el of overlays) {
    if (el instanceof HTMLElement) candidates.push(el);
  }

  const seen = new Set();
  const ordered = [];
  for (const item of candidates) {
    if (!(item instanceof HTMLElement)) continue;
    if (!isVisible(item) || !isScrollable(item)) continue;
    if (seen.has(item)) continue;
    seen.add(item);
    ordered.push(item);
  }
  if (!ordered.length) {
    return { scrolled: false };
  }

  const scoreForDirection = (el) => {
    const top = Number(el.scrollTop || 0);
    const left = Number(el.scrollLeft || 0);
    const maxTop = Math.max(0, Number(el.scrollHeight || 0) - Number(el.clientHeight || 0));
    const maxLeft = Math.max(0, Number(el.scrollWidth || 0) - Number(el.clientWidth || 0));
    const roomY = dy > 0
      ? Math.max(0, maxTop - top)
      : dy < 0
        ? Math.max(0, top)
        : Math.max(top, Math.max(0, maxTop - top));
    const roomX = dx > 0
      ? Math.max(0, maxLeft - left)
      : dx < 0
        ? Math.max(0, left)
        : Math.max(left, Math.max(0, maxLeft - left));
    const primaryRoom = Math.abs(dy) >= Math.abs(dx) ? roomY : roomX;
    const secondaryRoom = Math.abs(dy) >= Math.abs(dx) ? roomX : roomY;
    const area = Number(el.clientWidth || 0) * Number(el.clientHeight || 0);
    return {
      roomX,
      roomY,
      score: primaryRoom * 1000 + secondaryRoom * 100 + Math.min(area, 2_000_000) / 2000
    };
  };

  let target = null;
  let targetMeta = null;
  for (const candidate of ordered) {
    const meta = scoreForDirection(candidate);
    const hasRoom = meta.roomX > 1 || meta.roomY > 1;
    if (!hasRoom) continue;
    if (!targetMeta || meta.score > targetMeta.score) {
      target = candidate;
      targetMeta = meta;
    }
  }
  if (!(target instanceof HTMLElement)) {
    target = ordered[0];
    targetMeta = scoreForDirection(target);
  }

  const before = {
    left: Number(target.scrollLeft || 0),
    top: Number(target.scrollTop || 0),
  };
  if (typeof target.scrollBy === "function") {
    target.scrollBy(dx, dy);
  } else {
    target.scrollLeft = Number(target.scrollLeft || 0) + dx;
    target.scrollTop = Number(target.scrollTop || 0) + dy;
  }
  const after = {
    left: Number(target.scrollLeft || 0),
    top: Number(target.scrollTop || 0),
  };
  const scrolled = before.left !== after.left || before.top !== after.top;
  return {
    scrolled,
    before,
    after,
    role: String(target.getAttribute("role") || ""),
    aria_label: String(target.getAttribute("aria-label") || ""),
    container_key: buildContainerKey(target),
    room_x: Number(targetMeta?.roomX || 0),
    room_y: Number(targetMeta?.roomY || 0),
  };
}"""
