      function applyPatch(patch) {
        if (!appState.spec) {
          throw new Error("No active UI session to patch.");
        }
        if (!patch || typeof patch !== "object") {
          throw new Error("Invalid patch payload.");
        }
        const op = patch.op || "merge_spec";
        if (op === "replace_spec" && patch.spec) {
          renderSpec(patch.spec);
          return true;
        }
        if (op === "merge_spec" && patch.spec) {
          const nextSpec = mergeObjects(appState.spec, patch.spec);
          if (Array.isArray((appState.spec || {}).components) && Array.isArray((patch.spec || {}).components)) {
            nextSpec.components = mergeComponentList(
              (appState.spec || {}).components || [],
              (patch.spec || {}).components || [],
            );
          }
          if (patch.spec && typeof patch.spec === "object" && patch.spec.theme !== undefined) {
            const mergedTheme = normalizeTheme(patch.spec.theme);
            if (Object.keys(mergedTheme).length > 0) {
              appState.state = mergeObjects(appState.state || {}, {
                currentTheme: mergeObjects((appState.state || {}).currentTheme || {}, mergedTheme),
              });
            }
          }
          appState.spec = nextSpec;
          renderSpec(appState.spec);
          return true;
        }
        if (op === "update_component") {
          const targetId = String(patch.id || "").trim();
          if (!targetId) {
            throw new Error("update_component requires explicit patch.id.");
          }
          const component = getComponent(targetId);
          if (component) {
            if (patch.type) {
              const typeInfo = normalizeComponentType(patch.type);
              component.type = typeInfo.type;
            }
            component.props = mergeObjects(component.props || {}, patch.props || {});
            renderSpec(appState.spec);
            return true;
          }
          throw new Error("update_component target not found.");
        }
        if (op === "append_component" && patch.component) {
          const component = normalizeComponent(patch.component);
          appState.spec.components = (appState.spec.components || []).concat([component]);
          renderSpec(appState.spec);
          return true;
        }
        if (op === "remove_component" && patch.id) {
          appState.spec.components = (appState.spec.components || []).filter((item) => item.id !== patch.id);
          appState.spec.root = (appState.spec.root || []).filter((item) => item !== patch.id);
          renderSpec(appState.spec);
          return true;
        }
        if (op === "set_root" && Array.isArray(patch.root)) {
          appState.spec.root = patch.root;
          renderSpec(appState.spec);
          return true;
        }
        if (op === "set_title" && patch.title) {
          appState.spec.title = patch.title;
          renderSpec(appState.spec);
          return true;
        }
        if (!patch.op) {
          appState.spec = mergeObjects(appState.spec, patch);
          renderSpec(appState.spec);
          return true;
        }
        throw new Error("Unsupported patch operation: " + String(op));
      }

      function applyStatePatch(statePatch) {
        appState.state = mergeObjects(appState.state || {}, statePatch || {});
        if (appState.spec) {
          renderSpec(appState.spec);
        }
      }

      function decodeTypedValue(entry) {
        if (!entry || typeof entry !== "object") return null;
        if (entry.valueString !== undefined && entry.valueString !== null) return String(entry.valueString);
        if (entry.valueNumber !== undefined && entry.valueNumber !== null) return Number(entry.valueNumber);
        if (entry.valueBoolean !== undefined && entry.valueBoolean !== null) return Boolean(entry.valueBoolean);
        if (entry.valueNull === true) return null;
        if (Array.isArray(entry.valueList)) {
          return entry.valueList.map((item) => decodeTypedValue(item));
        }
        if (Array.isArray(entry.valueMap)) {
          const out = {};
          for (const child of entry.valueMap) {
            if (!child || typeof child !== "object") continue;
            const key = String(child.key || "").trim();
            if (!key) continue;
            out[key] = decodeTypedValue(child);
          }
          return out;
        }
        return null;
      }

      function decodeDataModelContents(contents) {
        const out = {};
        if (!Array.isArray(contents)) return out;
        for (const entry of contents) {
          if (!entry || typeof entry !== "object") continue;
          const key = String(entry.key || "").trim();
          if (!key) continue;
          out[key] = decodeTypedValue(entry);
        }
        return out;
      }

      function jsonPointerToPath(path) {
        const raw = String(path || "/").trim();
        if (!raw || raw === "/") return [];
        return raw
          .replace(/^\//, "")
          .split("/")
          .filter(Boolean)
          .map((part) => part.replace(/~1/g, "/").replace(/~0/g, "~"));
      }

      function setNestedAtPath(baseObject, path, patchObject) {
        if (!path.length) {
          if (patchObject && typeof patchObject === "object" && !Array.isArray(patchObject)) {
            return mergeObjects(baseObject || {}, patchObject);
          }
          return patchObject;
        }
        const root = mergeObjects(baseObject || {}, {});
        let current = root;
        for (let index = 0; index < path.length - 1; index += 1) {
          const key = path[index];
          const value = current[key];
          if (!value || typeof value !== "object" || Array.isArray(value)) {
            current[key] = {};
          }
          current = current[key];
        }
        const leaf = path[path.length - 1];
        const previous = current[leaf];
        if (patchObject && typeof patchObject === "object" && !Array.isArray(patchObject)) {
          current[leaf] = mergeObjects(previous || {}, patchObject);
        } else {
          current[leaf] = patchObject;
        }
        return root;
      }

      function removeNestedAtPath(baseObject, path) {
        if (!path.length) return {};
        const root = mergeObjects(baseObject || {}, {});
        let current = root;
        for (let index = 0; index < path.length - 1; index += 1) {
          const key = path[index];
          const value = current[key];
          if (!value || typeof value !== "object" || Array.isArray(value)) {
            return root;
          }
          current = value;
        }
        const leaf = path[path.length - 1];
        if (Object.prototype.hasOwnProperty.call(current, leaf)) {
          delete current[leaf];
        }
        return root;
      }

      function extractSurfaceComponentPayload(entry) {
        if (!entry || typeof entry !== "object") return null;
        const props = {};
        const rawComponent = entry.component;
        let componentType = "";

        if (typeof rawComponent === "string") {
          componentType = rawComponent.trim();
        } else if (rawComponent && typeof rawComponent === "object" && !Array.isArray(rawComponent)) {
          const typeEntries = Object.entries(rawComponent);
          if (typeEntries.length !== 1) {
            return null;
          }
          const [rawType, rawInlineProps] = typeEntries[0];
          componentType = String(rawType || "").trim();
          if (rawInlineProps && typeof rawInlineProps === "object" && !Array.isArray(rawInlineProps)) {
            for (const [key, value] of Object.entries(rawInlineProps)) {
              props[key] = value;
            }
          }
        }

        if (!componentType) {
          return null;
        }
        for (const [key, value] of Object.entries(entry)) {
          if (key === "id" || key === "component") continue;
          props[key] = value;
        }
        return { type: componentType, props };
      }

      function _normalizedSurfaceStoreLimit() {
        const raw = Number(appState.maxStoredSurfaces || 24);
        if (!Number.isFinite(raw)) return 24;
        return Math.max(4, Math.floor(raw));
      }

      function _removeSurfaceFromOrder(surfaceId) {
        const order = Array.isArray(appState.surfaceOrder) ? appState.surfaceOrder : [];
        appState.surfaceOrder = order.filter((item) => String(item || "").trim() !== surfaceId);
      }

      function _dropSurfaceState(surfaceId) {
        delete appState.surfaceStore[surfaceId];
        delete appState.dataModelStore[surfaceId];
        delete appState.surfaceMeta[surfaceId];
      }

      function _pruneSurfaceStores() {
        const order = Array.isArray(appState.surfaceOrder) ? appState.surfaceOrder : [];
        const limit = _normalizedSurfaceStoreLimit();
        if (order.length <= limit) {
          appState.surfaceOrder = order;
          return;
        }

        const activeUiId = appState.spec && appState.spec.ui_id
          ? String(appState.spec.ui_id).trim()
          : "";
        let guard = order.length * 2;
        while (order.length > limit && guard > 0) {
          guard -= 1;
          const candidate = String(order[0] || "").trim();
          if (!candidate) {
            order.shift();
            continue;
          }
          if (candidate === activeUiId) {
            order.push(order.shift());
            continue;
          }
          order.shift();
          _dropSurfaceState(candidate);
        }
        appState.surfaceOrder = order.slice(0, limit);
      }

      function _touchSurface(surfaceId) {
        const token = String(surfaceId || "").trim();
        if (!token) return;
        const order = Array.isArray(appState.surfaceOrder) ? appState.surfaceOrder : [];
        const next = order.filter((item) => String(item || "").trim() !== token);
        next.push(token);
        appState.surfaceOrder = next;
        _pruneSurfaceStores();
      }

      function applySurfaceUpdateMessage(message) {
        const surfaceId = String(message.surfaceId || "").trim();
        if (!surfaceId) {
          return { success: false, error: "updateComponents.surfaceId is required." };
        }
        const nextComponentById = {};
        let firstComponentId = "";
        let firstError = null;
        for (const item of (message.components || [])) {
          const componentId = String(item && item.id ? item.id : "").trim();
          if (!componentId) continue;
          if (!firstComponentId) {
            firstComponentId = componentId;
          }
          try {
            const payload = extractSurfaceComponentPayload(item);
            if (!payload || typeof payload !== "object") {
              throw new Error("invalid component payload shape");
            }
            const componentType = payload.type ? payload.type : "Text";
            const componentProps =
              payload.props && typeof payload.props === "object"
                ? payload.props
                : {};
            nextComponentById[componentId] = normalizeComponent({
              id: componentId,
              type: componentType,
              props: componentProps,
            });
          } catch (err) {
            firstError = String(err && err.message ? err.message : err);
            break;
          }
        }
        if (firstError) {
          showToast("updateComponents rejected invalid component: " + firstError, "error");
          return { success: false, error: firstError };
        }
        if (!Object.keys(nextComponentById).length) {
          showToast("updateComponents received empty/invalid component list.", "error");
          return { success: false, error: "updateComponents components are empty or invalid." };
        }
        const hasCanonicalRoot = Boolean(nextComponentById.root);
        const rootCandidate = hasCanonicalRoot
          ? "root"
          : (firstComponentId || Object.keys(nextComponentById)[0] || "");
        if (!rootCandidate) {
          showToast("updateComponents missing a valid root component.", "error");
          return { success: false, error: "updateComponents missing valid root component." };
        }
        if (!hasCanonicalRoot) {
          showToast(
            "updateComponents has no id='root'; using first component as root fallback.",
            "warning",
          );
        }

        appState.surfaceStore[surfaceId] = { componentById: nextComponentById };
        const previousMeta = appState.surfaceMeta[surfaceId] || {};
        appState.surfaceMeta[surfaceId] = mergeObjects(previousMeta, {
          rootId: String(rootCandidate).trim(),
        });
        _touchSurface(surfaceId);
        return { success: true, error: null };
      }

      function applyCreateSurfaceMessage(message) {
        const surfaceId = String(message.surfaceId || "").trim();
        if (!surfaceId) {
          return { success: false, error: "createSurface.surfaceId is required." };
        }
        appState.surfaceMeta[surfaceId] = mergeObjects(
          appState.surfaceMeta[surfaceId] || {},
          {
            sendDataModel: Boolean(message.sendDataModel),
            catalogId: String(message.catalogId || ""),
            rootId: "",
            hasBegunRendering: true,
            styles: {
              theme: (message.theme && typeof message.theme === "object") ? message.theme : {},
            },
          },
        );
        if (!appState.surfaceStore[surfaceId]) {
          appState.surfaceStore[surfaceId] = { componentById: {} };
        }
        if (!appState.dataModelStore[surfaceId]) {
          appState.dataModelStore[surfaceId] = {};
        }
        _touchSurface(surfaceId);
        return { success: true, error: null };
      }

      function buildSpecFromSurface(surfaceId, rootId) {
        const surface = appState.surfaceStore[surfaceId];
        if (!surface || !surface.componentById) return null;
        const components = Object.values(surface.componentById);
        if (!components.length) return null;
        const resolvedRoot = String(rootId || "").trim();
        if (!resolvedRoot) return null;
        if (!surface.componentById[resolvedRoot]) return null;
        const rootComponent = surface.componentById[resolvedRoot];
        const title =
          rootComponent &&
          rootComponent.props &&
          typeof rootComponent.props.title === "string" &&
          rootComponent.props.title.trim()
            ? rootComponent.props.title.trim()
            : "MetaUI Workspace";
        const styles =
          appState.surfaceMeta[surfaceId] && typeof appState.surfaceMeta[surfaceId].styles === "object"
            ? appState.surfaceMeta[surfaceId].styles
            : {};
        return sanitizeSpecForRender({
          spec_version: "1.0",
          ui_id: surfaceId,
          title,
          send_data_model: Boolean(
            appState.surfaceMeta[surfaceId] && appState.surfaceMeta[surfaceId].sendDataModel
          ),
          theme: styles.theme || {},
          components,
          root: [resolvedRoot],
          state_bindings: {},
        });
      }

      function tryRenderSurface(surfaceId, preferredRootId) {
        const meta = appState.surfaceMeta[surfaceId];
        if (!meta || !meta.hasBegunRendering) {
          return { success: false, error: "surface metadata missing or not ready." };
        }
        const preferred = String(preferredRootId || "").trim() || String(meta.rootId || "").trim();
        const spec = buildSpecFromSurface(surfaceId, preferred);
        if (!spec) {
          return { success: false, error: "unable to build renderable spec from surface state." };
        }
        appState.state = appState.dataModelStore[surfaceId] || {};
        try {
          renderSpec(spec);
        } catch (err) {
          return {
            success: false,
            error: "renderSpec failed: " + String(err && err.message ? err.message : err),
          };
        }
        return { success: true, error: null };
      }

      function applyDataModelUpdateMessage(message) {
        const surfaceId = String(message.surfaceId || "").trim();
        if (!surfaceId) {
          return { success: false, error: "updateDataModel.surfaceId is required." };
        }
        const path = jsonPointerToPath(message.path || "/");
        const hasValue = Object.prototype.hasOwnProperty.call(message || {}, "value");
        let patchObject;
        if (hasValue) {
          patchObject = message.value;
        } else {
          patchObject = decodeDataModelContents(message.contents || []);
        }
        const current = appState.dataModelStore[surfaceId] || {};
        if (!hasValue && !Array.isArray(message.contents)) {
          appState.dataModelStore[surfaceId] = removeNestedAtPath(current, path);
        } else {
          appState.dataModelStore[surfaceId] = setNestedAtPath(current, path, patchObject);
        }
        _touchSurface(surfaceId);
        const meta = appState.surfaceMeta[surfaceId];
        if (
          meta &&
          meta.hasBegunRendering &&
          appState.spec &&
          String(appState.spec.ui_id || "") === surfaceId
        ) {
          appState.state = appState.dataModelStore[surfaceId];
          try {
            renderSpec(appState.spec);
          } catch (err) {
            return {
              success: false,
              error: "renderSpec failed after updateDataModel: " + String(err && err.message ? err.message : err),
            };
          }
        }
        return { success: true, error: null };
      }

      function applyDeleteSurfaceMessage(message) {
        const surfaceId = String(message.surfaceId || "").trim();
        if (!surfaceId) {
          return { success: false, error: "deleteSurface.surfaceId is required." };
        }
        _dropSurfaceState(surfaceId);
        _removeSurfaceFromOrder(surfaceId);
        if (appState.spec && String(appState.spec.ui_id || "") === surfaceId) {
          releaseAllComponentCleanups();
          appState.spec = null;
          appState.state = {};
          contentEl.innerHTML = "<div class='small'>UI session closed.</div>";
        }
        return { success: true, error: null };
      }

      function handleLifecycleMessage(msg) {
        if (msg.createSurface) {
          const result = applyCreateSurfaceMessage(msg.createSurface);
          return { matched: true, success: Boolean(result && result.success), error: result && result.error };
        }
        if (msg.updateComponents) {
          const result = applySurfaceUpdateMessage(msg.updateComponents);
          if (result && result.success) {
            const surfaceId = String(msg.updateComponents.surfaceId || "").trim();
            if (surfaceId) {
              const meta = appState.surfaceMeta[surfaceId];
              const rootId = meta ? String(meta.rootId || "").trim() : "";
              const renderResult = tryRenderSurface(surfaceId, rootId);
              if (!renderResult || !renderResult.success) {
                return {
                  matched: true,
                  success: false,
                  error: renderResult && renderResult.error
                    ? renderResult.error
                    : "failed to render surface after updateComponents.",
                };
              }
            }
          }
          return {
            matched: true,
            success: Boolean(result && result.success),
            error: result && result.error,
          };
        }
        if (msg.updateDataModel) {
          const result = applyDataModelUpdateMessage(msg.updateDataModel);
          return { matched: true, success: Boolean(result && result.success), error: result && result.error };
        }
        if (msg.deleteSurface) {
          const result = applyDeleteSurfaceMessage(msg.deleteSurface);
          return { matched: true, success: Boolean(result && result.success), error: result && result.error };
        }
        return { matched: false, success: false, error: null };
      }

      function handleCommand(msg) {
        const lifecycle = handleLifecycleMessage(msg);
        if (lifecycle && lifecycle.matched) {
          if (!lifecycle.success) {
            const detail = String(lifecycle.error || "unknown lifecycle failure");
            showToast("Lifecycle apply failed: " + detail, "error");
            sendEvent("error", "runtime", {
              code: "LIFECYCLE_APPLY_FAILED",
              message: detail,
            });
          }
          return;
        }
        if (msg && typeof msg === "object" && msg.error && typeof msg.error === "object") {
          const code = String(msg.error.code || "ERROR");
          const text = String(msg.error.message || "client/runtime error");
          showToast(code + ": " + text, "error");
          return;
        }
        showToast("Unsupported message variant in strict A2UI mode.", "warning");
      }

      let _reconnectTimer = null;

      function nextReconnectDelayMs() {
        const attempt = Math.max(0, Number(appState.reconnectAttempt || 0));
        const delay = Math.min(
          RECONNECT_MAX_DELAY_MS,
          Math.round(RECONNECT_BASE_DELAY_MS * Math.pow(RECONNECT_MULTIPLIER, attempt)),
        );
        appState.reconnectAttempt = attempt + 1;
        return delay;
      }

      function scheduleReconnect() {
        if (_reconnectTimer) return;
        const delayMs = nextReconnectDelayMs();
        setStatus("Disconnected, reconnecting in " + (delayMs / 1000).toFixed(1) + "s...");
        _reconnectTimer = window.setTimeout(() => {
          _reconnectTimer = null;
          openSocket();
        }, delayMs);
      }

      function openSocket() {
        if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
        if (appState.ws && (appState.ws.readyState === WebSocket.OPEN || appState.ws.readyState === WebSocket.CONNECTING)) {
          return;
        }
        appState.socketGeneration = Number(appState.socketGeneration || 0) + 1;
        const generation = appState.socketGeneration;
        const ws = new WebSocket(WS_URL);
        appState.ws = ws;
        appState.helloAcked = false;
        ws.onopen = () => {
          if (generation !== appState.socketGeneration || ws !== appState.ws) return;
          appState.reconnectAttempt = 0;
          setStatus("Connected");
          ws.send(JSON.stringify({
            type: "hello",
            client_id: CLIENT_ID,
            token: TOKEN || null,
            protocol_versions: SUPPORTED_PROTOCOL_VERSIONS,
            supported_components: SUPPORTED_COMPONENTS,
            supported_commands: SUPPORTED_COMMANDS,
            features: SUPPORTED_FEATURES,
          }));
          // Show loading indicator if no spec has been rendered yet
          if (!appState.spec) {
            const contentEl = document.getElementById("content");
            if (contentEl && !contentEl.childElementCount) {
              contentEl.innerHTML = '<div style="padding:40px;text-align:center;color:#888;font-size:16px">'
                + 'Waiting for AI to generate UI\u2026</div>';
            }
          }
        };
        ws.onmessage = (evt) => {
          if (generation !== appState.socketGeneration || ws !== appState.ws) return;
          let msg;
          try {
            msg = JSON.parse(evt.data);
          } catch {
            return;
          }
          if (msg.type === "hello_ack") {
            appState.helloAcked = true;
            setStatus("Connected (" + (msg.client_id || CLIENT_ID) + ")");
            appState.catalog = msg.catalog || null;
            if (msg.auto_ui !== undefined) {
              showToast("auto_ui: " + (msg.auto_ui ? "on" : "off"), "info");
            }
            flushPendingEvents();
            return;
          }
          handleCommand(msg);
        };
        ws.onclose = () => {
          if (generation !== appState.socketGeneration) return;
          appState.helloAcked = false;
          scheduleReconnect();
        };
        ws.onerror = () => {
          if (generation !== appState.socketGeneration) return;
          appState.helloAcked = false;
          setStatus("Socket error, reconnecting...");
          if (ws.readyState === WebSocket.CLOSED) {
            scheduleReconnect();
          }
        };
      }

      openSocket();
