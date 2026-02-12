      const WS_URL = __WS_URL__;
      const TOKEN = __TOKEN__;
      const CLIENT_ID = "metaui-desktop";

      const titleEl = document.getElementById("title");
      const statusEl = document.getElementById("status");
      const contentEl = document.getElementById("content");
      const toastsEl = document.getElementById("toasts");

      const appState = {
        ws: null,
        spec: null,
        componentById: {},
        state: {},
        surfaceStore: {},
        dataModelStore: {},
        surfaceMeta: {},
        surfaceOrder: [],
        maxStoredSurfaces: 24,
        catalog: null,
        componentCleanupById: {},
        reconnectAttempt: 0,
        socketGeneration: 0,
        helloAcked: false,
        pendingEvents: [],
        lastOfflineToastAt: 0,
      };

      const RECONNECT_BASE_DELAY_MS = 350;
      const RECONNECT_MAX_DELAY_MS = 8000;
      const RECONNECT_MULTIPLIER = 1.7;
      const MAX_PENDING_EVENTS = 128;

      const SUPPORTED_PROTOCOL_VERSIONS = ["v0.10"];
      const SUPPORTED_COMPONENTS = [
        "Text",
        "Image",
        "Icon",
        "Video",
        "AudioPlayer",
        "Row",
        "Column",
        "List",
        "Card",
        "Tabs",
        "Modal",
        "Divider",
        "Button",
        "TextField",
        "CheckBox",
        "ChoicePicker",
        "Slider",
        "DateTimeInput",
      ];
      const SUPPORTED_COMMANDS = [
        "create_surface",
        "update_components",
        "update_data_model",
        "delete_surface",
      ];
      const SUPPORTED_FEATURES = [
        "a2ui_stream_v1",
        "json_pointer_bindings_v1",
      ];

      function setStatus(text) {
        statusEl.textContent = text;
      }

      function showToast(message, level) {
        const toast = document.createElement("div");
        toast.className = "toast " + (level || "info");
        toast.textContent = message;
        toastsEl.appendChild(toast);
        window.setTimeout(() => toast.remove(), 3600);
      }

      function registerComponentCleanup(componentId, cleanup) {
        const id = String(componentId || "").trim();
        if (!id || typeof cleanup !== "function") return;
        const existing = appState.componentCleanupById[id];
        if (Array.isArray(existing)) {
          existing.push(cleanup);
          return;
        }
        appState.componentCleanupById[id] = [cleanup];
      }

      function releaseComponentCleanupMap(cleanupMap) {
        const entries = Object.entries(cleanupMap || {});
        for (const [, cleanups] of entries) {
          if (!Array.isArray(cleanups)) continue;
          for (const cleanup of cleanups) {
            try {
              if (typeof cleanup === "function") cleanup();
            } catch (_error) {
              // ignore cleanup failures from detached nodes
            }
          }
        }
      }

      function releaseAllComponentCleanups() {
        const cleanupMap = appState.componentCleanupById || {};
        appState.componentCleanupById = {};
        releaseComponentCleanupMap(cleanupMap);
      }

      function enqueuePendingEvent(message) {
        if (!message || typeof message !== "object") return;
        const queue = Array.isArray(appState.pendingEvents) ? appState.pendingEvents : [];
        queue.push(message);
        while (queue.length > MAX_PENDING_EVENTS) {
          queue.shift();
        }
        appState.pendingEvents = queue;
      }

      function flushPendingEvents() {
        if (!appState.ws || appState.ws.readyState !== WebSocket.OPEN || !appState.helloAcked) {
          return;
        }
        const queue = Array.isArray(appState.pendingEvents) ? appState.pendingEvents : [];
        if (!queue.length) return;
        const remain = [];
        for (let index = 0; index < queue.length; index += 1) {
          const message = queue[index];
          try {
            appState.ws.send(JSON.stringify(message));
          } catch (_error) {
            remain.push(message);
            for (let rest = index + 1; rest < queue.length; rest += 1) {
              remain.push(queue[rest]);
            }
            break;
          }
        }
        appState.pendingEvents = remain;
      }

      function applyTheme(theme) {
        const presets = {
          dark: {
            "--bg-top": "#0b1220",
            "--bg-bottom": "#111827",
            "--panel": "#1f2937",
            "--text": "#e5e7eb",
            "--muted": "#9ca3af",
            "--border": "#374151",
            "--border-strong": "#4b5563",
            "--accent": "#22d3ee",
            "--accent-strong": "#06b6d4",
            "--accent-soft": "#164e63",
            "--focus-ring": "rgba(34, 211, 238, 0.35)",
            "--danger": "#f87171",
            "--warn": "#fbbf24",
          },
          light: {
            "--bg-top": "#f4f6fb",
            "--bg-bottom": "#e2e8f0",
            "--panel": "#ffffff",
            "--text": "#0f172a",
            "--muted": "#334155",
            "--border": "#cbd5e1",
            "--border-strong": "#94a3b8",
            "--accent": "#0f766e",
            "--accent-strong": "#115e59",
            "--accent-soft": "#d1fae5",
            "--focus-ring": "rgba(15, 118, 110, 0.22)",
            "--danger": "#be123c",
            "--warn": "#a16207",
          },
        };
        const vars = {
          color_bg_top: "--bg-top",
          color_bg_bottom: "--bg-bottom",
          color_surface: "--panel",
          color_text: "--text",
          color_muted: "--muted",
          color_border: "--border",
          color_border_strong: "--border-strong",
          color_primary: "--accent",
          color_primary_hover: "--accent-strong",
          color_primary_soft: "--accent-soft",
          color_focus_ring: "--focus-ring",
          shadow_soft: "--shadow-soft",
          shadow_panel: "--shadow-panel",
          color_danger: "--danger",
          color_warn: "--warn",
          color_panel_border: "--panel-border",
          radius_md: "--radius-md",
        };
        const normalized = normalizeTheme(theme);
        const root = document.documentElement;
        for (const cssVar of Object.values(vars)) {
          root.style.removeProperty(cssVar);
        }
        const modeToken = normalizeToken(normalized.mode || normalized.preset || "");
        const preset = modeToken === "dark" ? presets.dark : (modeToken === "light" ? presets.light : null);
        if (preset) {
          for (const [cssVar, cssValue] of Object.entries(preset)) {
            root.style.setProperty(cssVar, String(cssValue));
          }
        }
        for (const [key, value] of Object.entries(normalized)) {
          const cssVar = vars[key];
          if (!cssVar) continue;
          if (typeof value === "number" && key === "radius_md") {
            root.style.setProperty(cssVar, String(value) + "px");
          } else {
            root.style.setProperty(cssVar, String(value));
          }
        }
      }

      function normalizeComponentType(value) {
        const raw = String(value || "").trim();
        if (SUPPORTED_COMPONENTS.includes(raw)) {
          return { type: raw };
        }
        return { type: raw };
      }

      function normalizeOptionList(options) {
        if (!Array.isArray(options)) {
          throw new Error("ChoicePicker.props.options must be an array.");
        }
        const out = [];
        const resolveCtx = { state: appState.state || {}, payload: {}, event: {} };
        for (let index = 0; index < options.length; index += 1) {
          const item = options[index];
          if (item && typeof item === "object" && !Array.isArray(item)) {
            if (!Object.prototype.hasOwnProperty.call(item, "label") || !Object.prototype.hasOwnProperty.call(item, "value")) {
              throw new Error(
                "ChoicePicker.props.options[" + String(index) + "] requires both label and value."
              );
            }
            const rawValue = item.value !== undefined ? item.value : item.label;
            const rawLabel = item.label !== undefined ? item.label : rawValue;
            const resolvedValue = resolveTemplateValue(rawValue, resolveCtx);
            const resolvedLabel = resolveTemplateValue(rawLabel, resolveCtx);
            const value = resolvedValue !== undefined && resolvedValue !== null
              ? String(resolvedValue)
              : "";
            const label = resolvedLabel !== undefined && resolvedLabel !== null
              ? String(resolvedLabel)
              : value;
            if (!value && !label) continue;
            out.push({ label: label || value, value: value || label });
            continue;
          }
          throw new Error(
            "ChoicePicker.props.options[" + String(index) + "] must be an object."
          );
        }
        if (!out.length) {
          throw new Error("ChoicePicker.props.options must contain at least one valid option.");
        }
        return out;
      }

      function normalizeComponentRef(value) {
        if (value === undefined || value === null) return null;
        if (typeof value === "object") return null;
        const token = String(value).trim();
        return token || null;
      }

      function normalizeComponentRefList(values) {
        if (!Array.isArray(values)) return [];
        const out = [];
        for (let index = 0; index < values.length; index += 1) {
          const item = values[index];
          const ref = normalizeComponentRef(item);
          if (!ref) {
            throw new Error(
              "children[" + String(index) + "] must be a component id string."
            );
          }
          out.push(ref);
        }
        return out;
      }

      function normalizeChildListSpec(value, ownerName) {
        if (Array.isArray(value)) {
          return normalizeComponentRefList(value);
        }
        if (!value || typeof value !== "object" || Array.isArray(value)) {
          throw new Error(ownerName + " must be either an array of component ids or {componentId, path}.");
        }
        const componentId = normalizeComponentRef(value.componentId);
        const path = typeof value.path === "string" ? value.path.trim() : "";
        if (!componentId || !path) {
          throw new Error(ownerName + " template form requires both componentId and path.");
        }
        return { componentId, path };
      }

      function normalizeAxisLayoutProps(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["children", "justify", "align", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("Layout.props has unsupported key: " + String(key));
          }
        }
        out.children = normalizeChildListSpec(
          out.children,
          "Layout.props.children",
        );
        if (out.justify !== undefined && out.justify !== null) out.justify = String(out.justify);
        if (out.align !== undefined && out.align !== null) out.align = String(out.align);
        if (out.weight !== undefined && out.weight !== null) {
          const parsed = toFiniteNumber(out.weight);
          if (parsed !== null) out.weight = parsed;
        }
        return out;
      }

      function normalizeListPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["children", "direction", "align", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("List.props has unsupported key: " + String(key));
          }
        }
        out.children = normalizeChildListSpec(
          out.children,
          "List.props.children",
        );
        const direction = String(out.direction || "vertical").trim().toLowerCase();
        out.direction = direction === "horizontal" ? "horizontal" : "vertical";
        if (out.align !== undefined && out.align !== null) out.align = String(out.align);
        return out;
      }

      function normalizeCardPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["child", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("Card.props has unsupported key: " + String(key));
          }
        }
        const child = normalizeComponentRef(out.child);
        if (!child) {
          throw new Error("Card.props.child must be a component id.");
        }
        out.child = child;
        if (out.weight !== undefined && out.weight !== null) {
          const parsed = toFiniteNumber(out.weight);
          if (parsed !== null) out.weight = parsed;
        }
        return out;
      }

      function normalizeTabsPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["tabs", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("Tabs.props has unsupported key: " + String(key));
          }
        }
        const tabs = [];
        const rawTabs = Array.isArray(out.tabs) ? out.tabs : [];
        for (let index = 0; index < rawTabs.length; index += 1) {
          const item = rawTabs[index];
          if (!item || typeof item !== "object" || Array.isArray(item)) {
            throw new Error("Tabs.props.tabs[" + String(index) + "] must be an object.");
          }
          const title = String(item.title || "").trim();
          const child = normalizeComponentRef(item.child);
          if (!title || !child) {
            throw new Error(
              "Tabs.props.tabs[" + String(index) + "] requires both title and child."
            );
          }
          tabs.push({ title, child });
        }
        if (!tabs.length) {
          throw new Error("Tabs.props.tabs must contain at least one {title, child} entry.");
        }
        out.tabs = tabs;
        if (out.weight !== undefined && out.weight !== null) {
          const parsed = toFiniteNumber(out.weight);
          if (parsed !== null) out.weight = parsed;
        }
        return out;
      }

      function normalizeModalPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["trigger", "content", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("Modal.props has unsupported key: " + String(key));
          }
        }
        const trigger = normalizeComponentRef(out.trigger);
        const content = normalizeComponentRef(out.content);
        if (!trigger || !content) {
          throw new Error("Modal.props requires both trigger and content component ids.");
        }
        out.trigger = trigger;
        out.content = content;
        return out;
      }

      function normalizeButtonPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["child", "variant", "action", "checks", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("Button.props has unsupported key: " + String(key));
          }
        }
        const child = normalizeComponentRef(out.child);
        if (!child) {
          throw new Error("Button.props.child must be a component id.");
        }
        out.child = child;
        const variant = String(out.variant || "borderless").trim();
        out.variant = variant === "primary" ? "primary" : "borderless";
        if (!out.action || typeof out.action !== "object" || Array.isArray(out.action)) {
          throw new Error("Button.props.action must be an object.");
        }
        const hasEvent = out.action.event && typeof out.action.event === "object" && !Array.isArray(out.action.event);
        const hasFunctionCall =
          out.action.functionCall &&
          typeof out.action.functionCall === "object" &&
          !Array.isArray(out.action.functionCall);
        if (Boolean(hasEvent) === Boolean(hasFunctionCall)) {
          throw new Error("Button.props.action must include exactly one of {event, functionCall}.");
        }
        return out;
      }

      function normalizeTextFieldPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["label", "value", "variant", "checks", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("TextField.props has unsupported key: " + String(key));
          }
        }
        if (out.label === undefined || out.label === null || String(out.label).trim() === "") {
          throw new Error("TextField.props.label is required.");
        }
        const variant = String(out.variant || "shortText").trim();
        out.variant = ["longText", "number", "shortText", "obscured"].includes(variant)
          ? variant
          : "shortText";
        if (out.value === undefined || out.value === null) {
          out.value = "";
        }
        return out;
      }

      function normalizeCheckBoxPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["label", "value", "checks", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("CheckBox.props has unsupported key: " + String(key));
          }
        }
        if (out.label === undefined || out.label === null || String(out.label).trim() === "") {
          throw new Error("CheckBox.props.label is required.");
        }
        if (out.value === undefined) {
          throw new Error("CheckBox.props.value is required.");
        }
        return out;
      }

      function normalizeChoicePickerPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["label", "variant", "options", "value", "checks", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("ChoicePicker.props has unsupported key: " + String(key));
          }
        }
        if (!Array.isArray(out.options) || !out.options.length) {
          throw new Error("ChoicePicker.props.options must be a non-empty array.");
        }
        if (out.value === undefined) {
          throw new Error("ChoicePicker.props.value is required.");
        }
        if (out.label === undefined || out.label === null) {
          out.label = "";
        }
        const variant = String(out.variant || "mutuallyExclusive").trim();
        out.variant = variant === "multipleSelection" ? "multipleSelection" : "mutuallyExclusive";
        out.options = normalizeOptionList(out.options);
        if (out.variant === "multipleSelection") {
          if (Array.isArray(out.value)) {
            out.value = out.value.map((item) => String(item));
          } else if (out.value === undefined || out.value === null) {
            out.value = [];
          } else if (!(out.value && typeof out.value === "object" && !Array.isArray(out.value))) {
            out.value = [String(out.value)];
          }
        } else {
          if (Array.isArray(out.value)) {
            out.value = out.value.length ? String(out.value[0]) : "";
          } else if (out.value === undefined || out.value === null) {
            out.value = out.options.length ? String(out.options[0].value) : "";
          } else if (!(out.value && typeof out.value === "object" && !Array.isArray(out.value))) {
            out.value = String(out.value);
          }
        }
        return out;
      }

      function normalizeSliderPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["label", "value", "min", "max", "step", "checks", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("Slider.props has unsupported key: " + String(key));
          }
        }
        if (out.min === undefined || out.max === undefined || out.value === undefined) {
          throw new Error("Slider.props requires min, max, and value.");
        }
        out.label = out.label !== undefined && out.label !== null ? String(out.label) : "";
        let min = toFiniteNumber(out.min);
        let max = toFiniteNumber(out.max);
        let step = toFiniteNumber(out.step);
        const rawValue = out.value;
        let value = toFiniteNumber(rawValue);
        if (min === null || max === null || value === null) {
          if (min === null || max === null) {
            throw new Error("Slider.props.min/max must be finite numbers.");
          }
          if (!(rawValue && typeof rawValue === "object" && !Array.isArray(rawValue))) {
            throw new Error("Slider.props.value must be a finite number or dynamic binding object.");
          }
        }
        if (max < min) [min, max] = [max, min];
        step = step === null || step <= 0 ? 1 : step;
        if (value !== null) {
          value = Math.max(min, Math.min(max, value));
        }
        out.min = min;
        out.max = max;
        out.step = step;
        if (value !== null) {
          out.value = value;
        }
        return out;
      }

      function normalizeDateTimeInputPropsA2UI(props) {
        const out = mergeObjects({}, props || {});
        const allowed = new Set(["value", "enableDate", "enableTime", "min", "max", "label", "checks", "weight", "accessibility"]);
        for (const key of Object.keys(out)) {
          if (!allowed.has(String(key))) {
            throw new Error("DateTimeInput.props has unsupported key: " + String(key));
          }
        }
        if (out.value === undefined || out.value === null) {
          throw new Error("DateTimeInput.props.value is required.");
        }
        if (out.label === undefined || out.label === null) out.label = "";
        if (out.enableDate !== undefined && typeof out.enableDate !== "boolean") {
          throw new Error("DateTimeInput.props.enableDate must be a boolean.");
        }
        if (out.enableTime !== undefined && typeof out.enableTime !== "boolean") {
          throw new Error("DateTimeInput.props.enableTime must be a boolean.");
        }
        out.enableDate = out.enableDate !== undefined ? out.enableDate : true;
        out.enableTime = out.enableTime !== undefined ? out.enableTime : false;
        return out;
      }
