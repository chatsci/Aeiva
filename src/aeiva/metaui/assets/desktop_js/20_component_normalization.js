      function normalizeComponent(component) {
        if (!component || typeof component !== "object") return component;
        const normalized = mergeObjects({}, component);
        const rawType = normalized.type || normalized.component;
        const mergedProps = mergeObjects({}, normalized.props || {});
        for (const [key, value] of Object.entries(normalized)) {
          if (["id", "type", "component", "props"].includes(key)) continue;
          if (!(key in mergedProps)) mergedProps[key] = value;
        }
        normalized.props = mergedProps;
        const typeInfo = normalizeComponentType(rawType);
        normalized.type = typeInfo.type;
        if (!SUPPORTED_COMPONENTS.includes(normalized.type)) {
          throw new Error(
            "Unsupported component type: " + String(normalized.type || "") +
            ". Allowed: " + SUPPORTED_COMPONENTS.join(", ")
          );
        }

        normalized.props = mergeObjects({}, normalized.props || {});
        if (normalized.type === "Row" || normalized.type === "Column") {
          normalized.props = normalizeAxisLayoutProps(normalized.props);
        } else if (normalized.type === "List") {
          normalized.props = normalizeListPropsA2UI(normalized.props);
        } else if (normalized.type === "Card") {
          normalized.props = normalizeCardPropsA2UI(normalized.props);
        } else if (normalized.type === "Tabs") {
          normalized.props = normalizeTabsPropsA2UI(normalized.props);
        } else if (normalized.type === "Modal") {
          normalized.props = normalizeModalPropsA2UI(normalized.props);
        } else if (normalized.type === "Button") {
          normalized.props = normalizeButtonPropsA2UI(normalized.props);
        } else if (normalized.type === "TextField") {
          normalized.props = normalizeTextFieldPropsA2UI(normalized.props);
        } else if (normalized.type === "CheckBox") {
          normalized.props = normalizeCheckBoxPropsA2UI(normalized.props);
        } else if (normalized.type === "ChoicePicker") {
          normalized.props = normalizeChoicePickerPropsA2UI(normalized.props);
        } else if (normalized.type === "Slider") {
          normalized.props = normalizeSliderPropsA2UI(normalized.props);
        } else if (normalized.type === "DateTimeInput") {
          normalized.props = normalizeDateTimeInputPropsA2UI(normalized.props);
        } else if (normalized.type === "Text") {
          const allowed = new Set(["text", "variant", "weight", "accessibility"]);
          for (const key of Object.keys(normalized.props)) {
            if (!allowed.has(String(key))) {
              throw new Error("Text.props has unsupported key: " + String(key));
            }
          }
          normalized.props.text = normalizeDisplayPropValue(normalized.props.text, "");
          if (normalized.props.variant !== undefined && normalized.props.variant !== null) {
            const token = String(normalized.props.variant).trim();
            const variants = new Set(["h1", "h2", "h3", "h4", "h5", "caption", "body"]);
            if (!variants.has(token)) {
              throw new Error("Text.props.variant must be one of h1/h2/h3/h4/h5/caption/body.");
            }
            normalized.props.variant = token;
          }
        } else if (normalized.type === "Image" || normalized.type === "Video" || normalized.type === "AudioPlayer") {
          normalized.props.url = normalizeDisplayPropValue(normalized.props.url, "");
          if (typeof normalized.props.url === "string" && !normalized.props.url.trim()) {
            throw new Error(normalized.type + ".props.url is required.");
          }
          if (normalized.type === "Image") {
            const allowed = new Set(["url", "fit", "variant", "weight", "accessibility"]);
            for (const key of Object.keys(normalized.props)) {
              if (!allowed.has(String(key))) {
                throw new Error("Image.props has unsupported key: " + String(key));
              }
            }
          } else if (normalized.type === "Video") {
            const allowed = new Set(["url", "weight", "accessibility"]);
            for (const key of Object.keys(normalized.props)) {
              if (!allowed.has(String(key))) {
                throw new Error("Video.props has unsupported key: " + String(key));
              }
            }
          } else {
            const allowed = new Set(["url", "description", "weight", "accessibility"]);
            for (const key of Object.keys(normalized.props)) {
              if (!allowed.has(String(key))) {
                throw new Error("AudioPlayer.props has unsupported key: " + String(key));
              }
            }
          }
        } else if (normalized.type === "Icon") {
          const allowed = new Set(["name", "weight", "accessibility"]);
          for (const key of Object.keys(normalized.props)) {
            if (!allowed.has(String(key))) {
              throw new Error("Icon.props has unsupported key: " + String(key));
            }
          }
          normalized.props.name = normalizeDisplayPropValue(normalized.props.name, "");
        } else if (normalized.type === "Divider") {
          const allowed = new Set(["axis", "weight", "accessibility"]);
          for (const key of Object.keys(normalized.props)) {
            if (!allowed.has(String(key))) {
              throw new Error("Divider.props has unsupported key: " + String(key));
            }
          }
          if (normalized.props.axis !== undefined && normalized.props.axis !== null) {
            const axis = String(normalized.props.axis).trim();
            if (!["horizontal", "vertical"].includes(axis)) {
              throw new Error("Divider.props.axis must be 'horizontal' or 'vertical'.");
            }
            normalized.props.axis = axis;
          }
        }
        return normalized;
      }

      function normalizeDisplayPropValue(rawValue, fallbackValue) {
        if (rawValue === undefined || rawValue === null) {
          return fallbackValue;
        }
        if (
          typeof rawValue === "string" ||
          typeof rawValue === "number" ||
          typeof rawValue === "boolean"
        ) {
          return String(rawValue);
        }
        if (isObjectRecord(rawValue)) {
          // Keep structured template bindings (path/functionCall/etc.) untouched.
          return mergeObjects({}, rawValue);
        }
        if (Array.isArray(rawValue)) {
          return rawValue.slice();
        }
        return fallbackValue;
      }

      function mergeComponentList(baseComponents, incomingComponents) {
        const byId = {};
        const order = [];
        const passthrough = [];

        for (const raw of baseComponents || []) {
          const component = normalizeComponent(raw);
          if (!component || typeof component !== "object") continue;
          const id = typeof component.id === "string" ? component.id.trim() : "";
          if (!id) {
            passthrough.push(component);
            continue;
          }
          if (!(id in byId)) {
            order.push(id);
          }
          byId[id] = component;
        }

        for (const raw of incomingComponents || []) {
          const component = normalizeComponent(raw);
          if (!component || typeof component !== "object") continue;
          const id = typeof component.id === "string" ? component.id.trim() : "";
          if (!id) {
            passthrough.push(component);
            continue;
          }
          if (id in byId) {
            byId[id] = normalizeComponent(mergeObjects(byId[id], component));
          } else {
            byId[id] = component;
            order.push(id);
          }
        }

        const merged = [];
        for (const id of order) {
          if (byId[id]) merged.push(byId[id]);
        }
        return merged.concat(passthrough);
      }

      function resolveStatePath(source, path) {
        let key = String(path || "").trim();
        if (!key) return undefined;
        if (key.startsWith("$state.")) key = key.slice(7);
        if (key.startsWith("state.")) key = key.slice(6);
        const parts = key.split(".").filter(Boolean);
        let cursor = source;
        for (const part of parts) {
          if (!cursor || typeof cursor !== "object" || !(part in cursor)) {
            return undefined;
          }
          cursor = cursor[part];
        }
        return cursor;
      }

      function resolveBindingValue(binding, state) {
        if (typeof binding === "string") {
          return resolveStatePath(state, binding);
        }
        if (!binding || typeof binding !== "object") return undefined;
        if (Array.isArray(binding.paths)) {
          for (const path of binding.paths) {
            const value = resolveStatePath(state, path);
            if (value !== undefined && value !== null) return value;
          }
          return binding.default;
        }
        if (typeof binding.path === "string") {
          const value = resolveStatePath(state, binding.path);
          return value === undefined ? binding.default : value;
        }
        return undefined;
      }

      function applyStateBindings(spec, state) {
        const bindings = spec && spec.state_bindings;
        const next = mergeObjects({}, spec || {});
        next.components = (next.components || []).map((item) => normalizeComponent(item));
        if (!bindings || typeof bindings !== "object") {
          return next;
        }
        const index = {};
        for (const component of next.components) {
          index[component.id] = component;
        }
        for (const [componentId, mapping] of Object.entries(bindings)) {
          const target = index[componentId];
          if (!target || !mapping || typeof mapping !== "object") continue;
          target.props = mergeObjects({}, target.props || {});
          for (const [propName, descriptor] of Object.entries(mapping)) {
            const resolved = resolveBindingValue(descriptor, state || {});
            if (resolved !== undefined) {
              target.props[propName] = resolved;
            }
          }
          index[componentId] = normalizeComponent(target);
        }
        next.components = Object.values(index);
        return next;
      }

      function getComponent(componentId) {
        return appState.componentById[componentId] || null;
      }

      function shouldSendDataModelForCurrentSurface() {
        if (!appState.spec) return false;
        const uiId = String(appState.spec.ui_id || "").trim();
        if (!uiId) return false;
        const meta = appState.surfaceMeta[uiId];
        if (meta && typeof meta === "object" && typeof meta.sendDataModel === "boolean") {
          return Boolean(meta.sendDataModel);
        }
        if (appState.spec.send_data_model !== undefined) {
          return Boolean(appState.spec.send_data_model);
        }
        if (appState.spec.sendDataModel !== undefined) {
          return Boolean(appState.spec.sendDataModel);
        }
        return false;
      }

      function currentSurfaceDataModelSnapshot() {
        if (!appState.spec) return {};
        const uiId = String(appState.spec.ui_id || "").trim();
        if (!uiId) return mergeObjects({}, appState.state || {});
        const fromSurface = appState.dataModelStore[uiId];
        if (fromSurface && typeof fromSurface === "object") {
          return mergeObjects({}, fromSurface);
        }
        return mergeObjects({}, appState.state || {});
      }

      function eventComponentMetadata(componentId) {
        const id = String(componentId || "").trim();
        if (!id) return {};
        const component = getComponent(id);
        if (!component || typeof component !== "object") {
          return { component_id: id };
        }
        const props = isObjectRecord(component.props) ? component.props : {};
        const labelSource = props.label ?? props.title ?? props.text ?? props.placeholder;
        const metadata = {
          component_id: id,
          component_type: String(component.type || ""),
        };
        if (labelSource !== undefined && labelSource !== null) {
          metadata.component_label = String(labelSource);
        }
        if (props.name !== undefined && props.name !== null) {
          metadata.component_name = String(props.name);
        }
        return metadata;
      }

      function emitEvent(eventType, componentId, payload) {
        if (!appState.spec) {
          showToast("No active UI surface for event dispatch.", "warning");
          return;
        }
        const normalizedSurfaceId = String(appState.spec.ui_id || "unknown");
        const normalizedComponentId = String(componentId || "unknown");
        const normalizedEventType = String(eventType || "action");
        const normalizedPayload = isObjectRecord(payload) ? payload : {};
        const contextPayload = mergeObjects({}, normalizedPayload);
        const componentMeta = eventComponentMetadata(normalizedComponentId);
        const metaPayload = {};
        if (Object.keys(componentMeta).length) {
          metaPayload.component = componentMeta;
          metaPayload.source = "desktop_template";
        }
        if (shouldSendDataModelForCurrentSurface()) {
          metaPayload.a2uiClientDataModel = currentSurfaceDataModelSnapshot();
        }
        if (Object.keys(metaPayload).length) {
          contextPayload.__metaui = metaPayload;
        }
        const msg = {
          version: "v0.10",
          action: {
            name: normalizedEventType,
            surfaceId: normalizedSurfaceId,
            sourceComponentId: normalizedComponentId,
            timestamp: new Date().toISOString(),
            context: contextPayload,
          },
        };
        if (!appState.ws || appState.ws.readyState !== WebSocket.OPEN || !appState.helloAcked) {
          enqueuePendingEvent(msg);
          const now = Date.now();
          if ((now - Number(appState.lastOfflineToastAt || 0)) > 1500) {
            showToast("Connection lost. Reconnecting...", "warning");
            appState.lastOfflineToastAt = now;
          }
          return;
        }
        try {
          flushPendingEvents();
          appState.ws.send(JSON.stringify(msg));
        } catch (_error) {
          enqueuePendingEvent(msg);
          appState.helloAcked = false;
          const now = Date.now();
          if ((now - Number(appState.lastOfflineToastAt || 0)) > 1500) {
            showToast("Connection lost. Reconnecting...", "warning");
            appState.lastOfflineToastAt = now;
          }
          if (typeof scheduleReconnect === "function") {
            scheduleReconnect();
          }
        }
      }

      function currentSurfaceId() {
        if (!appState.spec) return "";
        return String(appState.spec.ui_id || "").trim();
      }

      function writeValueToDataModel(path, value) {
        const key = String(path || "").trim();
        if (!key) return false;
        if (key.startsWith("/")) {
          const surfaceId = currentSurfaceId();
          const pointer = jsonPointerToPath(key);
          appState.state = setNestedAtPath(appState.state || {}, pointer, value);
          if (surfaceId) {
            const current = appState.dataModelStore[surfaceId] || {};
            appState.dataModelStore[surfaceId] = setNestedAtPath(current, pointer, value);
          }
          return true;
        }
        const normalizedPath = key.startsWith("$state.")
          ? key.slice(7)
          : (key.startsWith("state.") ? key.slice(6) : key);
        if (!normalizedPath) return false;
        setStateValueAtPath(normalizedPath, value, "set");
        const surfaceId = currentSurfaceId();
        if (surfaceId) {
          appState.dataModelStore[surfaceId] = mergeObjects({}, appState.state || {});
        }
        return true;
      }

      function applyValueBinding(rawBinding, value) {
        if (!rawBinding || typeof rawBinding !== "object" || Array.isArray(rawBinding)) {
          return false;
        }
        if (typeof rawBinding.path !== "string") {
          return false;
        }
        return writeValueToDataModel(rawBinding.path, value);
      }

      function resolveActionContext(contextRaw, eventContext) {
        if (!contextRaw || typeof contextRaw !== "object" || Array.isArray(contextRaw)) {
          return {};
        }
        const resolved = resolveTemplateValue(contextRaw, eventContext);
        if (resolved && typeof resolved === "object" && !Array.isArray(resolved)) {
          return resolved;
        }
        return {};
      }

      function executeA2uiAction(component, eventType, payload, renderContext) {
        if (!component || typeof component !== "object") return false;
        const props = component.props && typeof component.props === "object" ? component.props : {};
        const action = props.action;
        if (!action || typeof action !== "object" || Array.isArray(action)) {
          return false;
        }

        const eventContext = mergeObjects({
          state: currentSurfaceDataModelSnapshot(),
          payload: payload && typeof payload === "object" ? payload : {},
          event: {
            type: String(eventType || "action"),
            component_id: String(component.id || ""),
          },
          component,
          componentId: String(component.id || ""),
          sourceComponentId: String(component.id || ""),
          eventType: String(eventType || "action"),
        }, isObjectRecord(renderContext) ? renderContext : {});

        if (action.event && typeof action.event === "object" && !Array.isArray(action.event)) {
          const name = String(action.event.name || "").trim();
          if (!name) {
            showToast("Button action.event.name is required.", "error");
            return false;
          }
          const context = resolveActionContext(action.event.context, eventContext);
          emitEvent(name, component.id, context);
          return true;
        }

        if (
          action.functionCall &&
          typeof action.functionCall === "object" &&
          !Array.isArray(action.functionCall)
        ) {
          const callSpec = action.functionCall;
          const callName = String(callSpec.call || callSpec.name || "").trim();
          if (!callName) {
            showToast("Button action.functionCall.call is required.", "error");
            return false;
          }
          const normalizedCallName = normalizeToken(callName);
          const args = isObjectRecord(callSpec.args)
            ? (
              normalizedCallName === "run_sequence"
                ? mergeObjects({}, callSpec.args)
                : resolveTemplateValue(callSpec.args, eventContext)
            )
            : {};
          const result = resolveFunctionCallValue(callName, args, eventContext);
          if (result === null) {
            showToast("Unsupported functionCall: " + callName, "warning");
            emitEvent(
              "function_call",
              component.id,
              {
                call: callName,
                args: isObjectRecord(args) ? args : {},
                source: "button.functionCall",
                status: "unsupported",
              },
            );
            return true;
          }
          emitEvent(
            "function_result",
            component.id,
            {
              call: callName,
              args: isObjectRecord(args) ? args : {},
              result,
              source: "button.functionCall",
            },
          );
          return true;
        }

        return false;
      }

      function normalizeEventName(value, fallback) {
        const text = String(value || "").trim();
        if (text) return text;
        const fallbackText = String(fallback || "").trim();
        return fallbackText || "event";
      }

      function sendEvent(eventType, componentId, payload) {
        emitEvent(eventType, componentId, payload);
      }

      function setStateValueAtPath(path, value, operation) {
        const key = String(path || "").trim();
        const op = normalizeToken(operation || "set");
        if (!key) {
          if ((op === "merge" || op === "merge_state") && value && typeof value === "object" && !Array.isArray(value)) {
            appState.state = mergeObjects(appState.state || {}, value);
          } else {
            appState.state = value;
          }
          return;
        }

        const parts = key.split(".").filter(Boolean);
        const nextState = mergeObjects({}, appState.state || {});
        let cursor = nextState;
        for (let i = 0; i < parts.length - 1; i += 1) {
          const part = parts[i];
          const existing = cursor[part];
          if (!existing || typeof existing !== "object" || Array.isArray(existing)) {
            cursor[part] = {};
          } else {
            cursor[part] = mergeObjects({}, existing);
          }
          cursor = cursor[part];
        }
        const leaf = parts[parts.length - 1];
        const current = cursor[leaf];
        if (op === "append") {
          const arr = Array.isArray(current) ? current.slice() : [];
          arr.push(value);
          cursor[leaf] = arr;
        } else if (op === "prepend") {
          const arr = Array.isArray(current) ? current.slice() : [];
          arr.unshift(value);
          cursor[leaf] = arr;
        } else if (op === "merge" || op === "merge_state") {
          if (current && typeof current === "object" && !Array.isArray(current) && value && typeof value === "object" && !Array.isArray(value)) {
            cursor[leaf] = mergeObjects(current, value);
          } else {
            cursor[leaf] = value;
          }
        } else if (op === "delete" || op === "remove") {
          delete cursor[leaf];
        } else {
          cursor[leaf] = value;
        }
        appState.state = nextState;
      }


      function resolvePathFromObject(source, path) {
        if (!source || typeof source !== "object") return undefined;
        const key = String(path || "").trim();
        if (!key) return undefined;
        const parts = key.split(".").filter(Boolean);
        let cursor = source;
        for (const part of parts) {
          if (!cursor || typeof cursor !== "object" || !(part in cursor)) {
            return undefined;
          }
          cursor = cursor[part];
        }
        return cursor;
      }

      function resolveTemplateToken(path, context) {
        const key = String(path || "").trim();
        if (!key) return undefined;
        if (key === ".") {
          if (context.item !== undefined) return context.item;
          if (context.payload !== undefined) return context.payload;
          return context.state;
        }
        if (key.startsWith("item.")) {
          const item = context.item;
          if (item !== undefined && (item === null || typeof item !== "object")) {
            return item;
          }
        }
        if (key.startsWith("/")) {
          const parts = key
            .replace(/^\//, "")
            .split("/")
            .filter(Boolean)
            .map((part) => part.replace(/~1/g, "/").replace(/~0/g, "~"));
          let cursor = context.state || {};
          for (const part of parts) {
            if (!cursor || typeof cursor !== "object" || !(part in cursor)) return undefined;
            cursor = cursor[part];
          }
          return cursor;
        }
        if (key.startsWith("state.")) {
          return resolvePathFromObject(context.state || {}, key.slice(6));
        }
        if (key.startsWith("$state.")) {
          return resolvePathFromObject(context.state || {}, key.slice(7));
        }
        if (key.startsWith("payload.")) {
          return resolvePathFromObject(context.payload || {}, key.slice(8));
        }
        if (key.startsWith("event.")) {
          return resolvePathFromObject(context.event || {}, key.slice(6));
        }
        const direct = resolvePathFromObject(context, key);
        if (direct !== undefined) return direct;
        const payloadValue = resolvePathFromObject(context.payload || {}, key);
        if (payloadValue !== undefined) return payloadValue;
        return resolvePathFromObject(context.state || {}, key);
      }

      function _normalizeStateMutationPath(rawPath) {
        const key = String(rawPath || "").trim();
        if (!key) return "";
        if (key.startsWith("$state.")) return key.slice(7);
        if (key.startsWith("state.")) return key.slice(6);
        return key;
      }

      function _readNestedAtPath(baseObject, pathParts) {
        let cursor = baseObject;
        for (const part of pathParts) {
          if (cursor === null || cursor === undefined) return undefined;
          if (typeof cursor !== "object" || Array.isArray(cursor)) return undefined;
          if (!Object.prototype.hasOwnProperty.call(cursor, part)) return undefined;
          cursor = cursor[part];
        }
        return cursor;
      }

      function _rerenderActiveSurfaceAfterLocalMutation() {
        if (!appState.spec || typeof renderSpec !== "function") {
          return;
        }
        try {
          renderSpec(appState.spec);
        } catch (_err) {
          // Keep local state mutation effective even if visual refresh fails.
          // Runtime error channel already reports render failures separately.
        }
      }

      function _applyLocalStateMutation(callName, argMap) {
        const path = _normalizeStateMutationPath(argMap.path);
        if (!path) return undefined;

        if (callName === "setState") {
          writeValueToDataModel(path, argMap.value);
          _rerenderActiveSurfaceAfterLocalMutation();
          return undefined;
        }

        if (path.startsWith("/")) {
          const pointer = jsonPointerToPath(path);
          const surfaceId = currentSurfaceId();
          const currentState = mergeObjects({}, appState.state || {});
          const currentValue = _readNestedAtPath(currentState, pointer);
          let nextState = currentState;

          if (callName === "deleteState") {
            nextState = removeNestedAtPath(currentState, pointer);
          } else if (callName === "appendState") {
            const list = Array.isArray(currentValue) ? currentValue.slice() : [];
            list.push(argMap.value);
            nextState = setNestedAtPath(currentState, pointer, list);
          } else if (callName === "prependState") {
            const list = Array.isArray(currentValue) ? currentValue.slice() : [];
            list.unshift(argMap.value);
            nextState = setNestedAtPath(currentState, pointer, list);
          } else if (callName === "mergeState") {
            const currentMap = (currentValue && typeof currentValue === "object" && !Array.isArray(currentValue))
              ? currentValue
              : {};
            const incomingMap = (argMap.value && typeof argMap.value === "object" && !Array.isArray(argMap.value))
              ? argMap.value
              : {};
            nextState = setNestedAtPath(currentState, pointer, mergeObjects(currentMap, incomingMap));
          }

          appState.state = nextState;
          if (surfaceId) {
            appState.dataModelStore[surfaceId] = mergeObjects({}, nextState);
          }
          _rerenderActiveSurfaceAfterLocalMutation();
          return undefined;
        }

        if (callName === "deleteState") {
          setStateValueAtPath(path, null, "delete");
        } else if (callName === "appendState") {
          setStateValueAtPath(path, argMap.value, "append");
        } else if (callName === "prependState") {
          setStateValueAtPath(path, argMap.value, "prepend");
        } else if (callName === "mergeState") {
          setStateValueAtPath(path, argMap.value, "merge");
        }
        const surfaceId = currentSurfaceId();
        if (surfaceId) {
          appState.dataModelStore[surfaceId] = mergeObjects({}, appState.state || {});
        }
        _rerenderActiveSurfaceAfterLocalMutation();
        return undefined;
      }

      function _matchedFunctionResult(value) {
        return { matched: true, value };
      }

      function _unmatchedFunctionResult() {
        return { matched: false, value: null };
      }

      function resolveValidationFunctionCall(name, argMap) {
        if (name === "required") {
          const value = argMap.value;
          if (value === undefined || value === null) return _matchedFunctionResult(false);
          if (typeof value === "string") return _matchedFunctionResult(value.trim().length > 0);
          if (Array.isArray(value)) return _matchedFunctionResult(value.length > 0);
          if (typeof value === "object") return _matchedFunctionResult(Object.keys(value).length > 0);
          return _matchedFunctionResult(Boolean(value));
        }
        if (name === "email") {
          const value = String(argMap.value || "").trim();
          return _matchedFunctionResult(/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value));
        }
        if (name === "regex") {
          const value = String(argMap.value || "");
          const pattern = String(argMap.pattern || "");
          if (!pattern) return _matchedFunctionResult(false);
          try {
            return _matchedFunctionResult(Boolean(new RegExp(pattern).test(value)));
          } catch (_error) {
            return _matchedFunctionResult(false);
          }
        }
        if (name === "length") {
          const value = argMap.value;
          const size = Array.isArray(value) || typeof value === "string"
            ? value.length
            : (value && typeof value === "object" ? Object.keys(value).length : 0);
          if (argMap.min !== undefined && size < Number(argMap.min)) return _matchedFunctionResult(false);
          if (argMap.max !== undefined && size > Number(argMap.max)) return _matchedFunctionResult(false);
          return _matchedFunctionResult(true);
        }
        if (name === "numeric") {
          const number = Number(argMap.value);
          if (!Number.isFinite(number)) return _matchedFunctionResult(false);
          if (argMap.min !== undefined && number < Number(argMap.min)) return _matchedFunctionResult(false);
          if (argMap.max !== undefined && number > Number(argMap.max)) return _matchedFunctionResult(false);
          return _matchedFunctionResult(true);
        }
        return _unmatchedFunctionResult();
      }

      function resolveFormattingFunctionCall(name, argMap, context) {
        if (name === "formatString") {
          const template = String(argMap.value || "");
          if (!template) return _matchedFunctionResult("");
          return _matchedFunctionResult(
            template
              .replace(/\$\{([^}]+)\}/g, (_match, rawToken) => {
                const token = String(rawToken || "").trim();
                const resolved = resolveTemplateToken(token, context || {});
                if (resolved === undefined || resolved === null) return "";
                if (typeof resolved === "object") return JSON.stringify(resolved);
                return String(resolved);
              })
              .replace(/\\\$\{/g, "${")
          );
        }
        if (name === "formatNumber") {
          const value = Number(argMap.value);
          if (!Number.isFinite(value)) return _matchedFunctionResult(String(argMap.value ?? ""));
          const decimals = Number.isFinite(Number(argMap.decimals)) ? Number(argMap.decimals) : undefined;
          const grouping = argMap.grouping === undefined ? true : Boolean(argMap.grouping);
          return _matchedFunctionResult(
            value.toLocaleString(undefined, {
              minimumFractionDigits: decimals === undefined ? 0 : Math.max(0, decimals),
              maximumFractionDigits: decimals === undefined ? 2 : Math.max(0, decimals),
              useGrouping: grouping,
            })
          );
        }
        if (name === "formatCurrency") {
          const value = Number(argMap.value);
          const currency = String(argMap.currency || "USD").toUpperCase();
          if (!Number.isFinite(value)) return _matchedFunctionResult(String(argMap.value ?? ""));
          const decimals = Number.isFinite(Number(argMap.decimals)) ? Number(argMap.decimals) : undefined;
          return _matchedFunctionResult(
            value.toLocaleString(undefined, {
              style: "currency",
              currency,
              minimumFractionDigits: decimals === undefined ? 2 : Math.max(0, decimals),
              maximumFractionDigits: decimals === undefined ? 2 : Math.max(0, decimals),
              useGrouping: argMap.grouping === undefined ? true : Boolean(argMap.grouping),
            })
          );
        }
        if (name === "formatDate") {
          const raw = argMap.value;
          if (raw === undefined || raw === null || raw === "") return _matchedFunctionResult("");
          const date = new Date(raw);
          if (Number.isNaN(date.getTime())) return _matchedFunctionResult(String(raw));
          const format = String(argMap.format || "").trim();
          if (!format) return _matchedFunctionResult(date.toISOString());
          const map = {
            YYYY: String(date.getFullYear()),
            MM: String(date.getMonth() + 1).padStart(2, "0"),
            dd: String(date.getDate()).padStart(2, "0"),
            h: String((date.getHours() % 12) || 12),
            hh: String((date.getHours() % 12) || 12).padStart(2, "0"),
            mm: String(date.getMinutes()).padStart(2, "0"),
            ss: String(date.getSeconds()).padStart(2, "0"),
            a: date.getHours() >= 12 ? "PM" : "AM",
            E: date.toLocaleDateString(undefined, { weekday: "short" }),
            MMM: date.toLocaleDateString(undefined, { month: "short" }),
          };
          return _matchedFunctionResult(
            format
              .replace(/YYYY/g, map.YYYY)
              .replace(/MMM/g, map.MMM)
              .replace(/MM/g, map.MM)
              .replace(/dd/g, map.dd)
              .replace(/hh/g, map.hh)
              .replace(/h/g, map.h)
              .replace(/mm/g, map.mm)
              .replace(/ss/g, map.ss)
              .replace(/a/g, map.a)
              .replace(/E/g, map.E)
          );
        }
        if (name === "pluralize") {
          const value = Number(argMap.value);
          if (!Number.isFinite(value)) return _matchedFunctionResult(String(argMap.other || ""));
          if (value === 0 && argMap.zero !== undefined) return _matchedFunctionResult(String(argMap.zero));
          if (value === 1 && argMap.one !== undefined) return _matchedFunctionResult(String(argMap.one));
          if (value === 2 && argMap.two !== undefined) return _matchedFunctionResult(String(argMap.two));
          if (Number.isInteger(value) && Math.abs(value) >= 3 && Math.abs(value) <= 4 && argMap.few !== undefined) {
            return _matchedFunctionResult(String(argMap.few));
          }
          if (Number.isInteger(value) && Math.abs(value) >= 5 && argMap.many !== undefined) {
            return _matchedFunctionResult(String(argMap.many));
          }
          return _matchedFunctionResult(String(argMap.other || ""));
        }
        return _unmatchedFunctionResult();
      }

      function resolveStateFunctionCall(name, argMap, context, depth) {
        if (name === "openUrl") {
          const url = String(argMap.url || "").trim();
          if (url) {
            window.open(url, "_blank", "noopener,noreferrer");
          }
          return _matchedFunctionResult(undefined);
        }
        if (name === "runSequence") {
          const steps = Array.isArray(argMap.steps) ? argMap.steps : [];
          if (!steps.length) {
            return _matchedFunctionResult(undefined);
          }
          const results = [];
          for (const step of steps) {
            if (!step || typeof step !== "object" || Array.isArray(step)) {
              continue;
            }
            const stepCall = String(step.call || step.name || "").trim();
            if (!stepCall) {
              continue;
            }
            if (normalizeToken(stepCall) === "run_sequence") {
              continue;
            }
            const stepArgs = (step.args && typeof step.args === "object" && !Array.isArray(step.args))
              ? step.args
              : {};
            results.push(resolveFunctionCallValue(stepCall, stepArgs, context, depth + 1));
          }
          return _matchedFunctionResult(results);
        }
        if (
          name === "setState" ||
          name === "deleteState" ||
          name === "appendState" ||
          name === "prependState" ||
          name === "mergeState"
        ) {
          return _matchedFunctionResult(_applyLocalStateMutation(name, argMap));
        }
        return _unmatchedFunctionResult();
      }

      function resolveLogicFunctionCall(name, argMap, values) {
        if (name === "and") {
          if (!Array.isArray(values) || values.length < 2) return _matchedFunctionResult(false);
          return _matchedFunctionResult(values.every((item) => Boolean(item)));
        }
        if (name === "or") {
          if (!Array.isArray(values) || values.length < 2) return _matchedFunctionResult(false);
          return _matchedFunctionResult(values.some((item) => Boolean(item)));
        }
        if (name === "not") {
          return _matchedFunctionResult(!Boolean(argMap.value));
        }
        return _unmatchedFunctionResult();
      }

      function resolveFunctionCallValue(callName, args, context, depth) {
        const name = String(callName || "").trim();
        const normalizedName = normalizeToken(name);
        const safeDepth = Number.isFinite(depth) ? Number(depth) : 0;
        if (safeDepth > 8) {
          return null;
        }
        const argMap = (args && typeof args === "object" && !Array.isArray(args))
          ? (
            normalizedName === "run_sequence"
              ? mergeObjects({}, args)
              : resolveTemplateValue(args, context)
          )
          : {};
        const values = Array.isArray(argMap && argMap.values) ? argMap.values : null;

        const resolvers = [
          () => resolveValidationFunctionCall(name, argMap),
          () => resolveFormattingFunctionCall(name, argMap, context),
          () => resolveStateFunctionCall(name, argMap, context, safeDepth),
          () => resolveLogicFunctionCall(name, argMap, values),
        ];
        for (const resolve of resolvers) {
          const result = resolve();
          if (result.matched) return result.value;
        }
        return null;
      }

      function tryResolveStructuredValue(value, context) {
        if (!value || typeof value !== "object" || Array.isArray(value)) {
          return { matched: false, value: undefined };
        }
        const keys = Object.keys(value);
        if ("literal" in value) {
          return { matched: true, value: value.literal };
        }
        if ("literalString" in value) {
          return { matched: true, value: value.literalString ?? "" };
        }
        if ("literalNumber" in value) {
          return { matched: true, value: Number(value.literalNumber ?? 0) };
        }
        if ("literalBoolean" in value) {
          return { matched: true, value: Boolean(value.literalBoolean) };
        }
        if ("literalArray" in value && Array.isArray(value.literalArray)) {
          return { matched: true, value: value.literalArray.slice() };
        }
        if ("literalObject" in value && value.literalObject && typeof value.literalObject === "object") {
          return { matched: true, value: mergeObjects({}, value.literalObject) };
        }
        if (
          "path" in value &&
          keys.every((key) => ["path", "default", "fallback"].includes(String(key)))
        ) {
          const path = String(value.path || "").trim();
          const resolved = path ? resolveTemplateToken(path, context) : undefined;
          if ((resolved === undefined || resolved === null) && value.default !== undefined) {
            return { matched: true, value: value.default };
          }
          if ((resolved === undefined || resolved === null) && value.fallback !== undefined) {
            return { matched: true, value: value.fallback };
          }
          return { matched: true, value: resolved };
        }
        if (
          ("$state" in value || "$ref" in value) &&
          keys.every((key) => ["$state", "$ref", "default", "fallback"].includes(String(key)))
        ) {
          const ref = String(value.$state || value.$ref || "").trim();
          const resolved = ref ? resolveTemplateToken(ref, context) : undefined;
          if ((resolved === undefined || resolved === null) && value.default !== undefined) {
            return { matched: true, value: value.default };
          }
          if ((resolved === undefined || resolved === null) && value.fallback !== undefined) {
            return { matched: true, value: value.fallback };
          }
          return { matched: true, value: resolved };
        }
        if (
          "call" in value &&
          keys.every((key) => ["call", "args", "returnType", "default", "fallback"].includes(String(key)))
        ) {
          return {
            matched: true,
            value: resolveFunctionCallValue(value.call, value.args || {}, context),
          };
        }
        if (
          "functionCall" in value &&
          value.functionCall &&
          typeof value.functionCall === "object" &&
          !Array.isArray(value.functionCall) &&
          keys.every((key) => ["functionCall", "default", "fallback"].includes(String(key)))
        ) {
          const callSpec = value.functionCall;
          return {
            matched: true,
            value: resolveFunctionCallValue(callSpec.call || callSpec.name || "", callSpec.args || {}, context),
          };
        }
        return { matched: false, value: undefined };
      }

      function resolveTemplateValue(value, context) {
        const structured = tryResolveStructuredValue(value, context);
        if (structured.matched) {
          return structured.value;
        }
        if (typeof value === "string") {
          const exact = value.match(/^\s*(?:\$\{([^}]+)\}|\{\{([^}]+)\}\})\s*$/);
          if (exact) {
            const token = (exact[1] || exact[2] || "").trim();
            const resolved = resolveTemplateToken(token, context);
            return resolved === undefined ? value : resolved;
          }
          return value.replace(/\$\{([^}]+)\}|\{\{([^}]+)\}\}/g, (_match, p1, p2) => {
            const token = String(p1 || p2 || "").trim();
            const resolved = resolveTemplateToken(token, context);
            if (resolved === undefined || resolved === null) return "";
            if (typeof resolved === "object") return JSON.stringify(resolved);
            return String(resolved);
          });
        }
        if (Array.isArray(value)) {
          return value.map((item) => resolveTemplateValue(item, context));
        }
        if (value && typeof value === "object") {
          const out = {};
          for (const [key, item] of Object.entries(value)) {
            out[key] = resolveTemplateValue(item, context);
          }
          return out;
        }
        return value;
      }

      function renderValue(rawValue, overrides) {
        const context = mergeObjects(
          {
            state: appState.state || {},
            payload: {},
            event: {},
          },
          overrides || {},
        );
        return resolveTemplateValue(rawValue, context);
      }

      function valueAsString(rawValue, fallback, overrides) {
        const value = renderValue(rawValue, overrides);
        if (value === undefined || value === null) return String(fallback || "");
        return String(value);
      }

      function valueAsBoolean(rawValue, fallback, overrides) {
        const value = renderValue(rawValue, overrides);
        if (value === undefined || value === null) return Boolean(fallback);
        return Boolean(value);
      }
