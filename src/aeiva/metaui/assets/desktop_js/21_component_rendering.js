      function dispatchComponentEvent(component, eventType, basePayload, options) {
        if (!component || typeof component !== "object") return;
        const payload = isObjectRecord(basePayload) ? basePayload : {};
        const renderContext = isObjectRecord(options && options.renderContext)
          ? options.renderContext
          : {};
        const executed = executeA2uiAction(component, eventType, payload, renderContext);
        if (executed) {
          return;
        }
        const shouldEmit = options && Object.prototype.hasOwnProperty.call(options, "emitWhenNoAction")
          ? Boolean(options.emitWhenNoAction)
          : true;
        if (shouldEmit) {
          sendEvent(normalizeEventName(eventType, "event"), component.id, payload);
        }
      }

      function attachComponentListener(component, element, domEvent, listener) {
        if (!element || typeof element.addEventListener !== "function" || typeof listener !== "function") {
          return;
        }
        element.addEventListener(domEvent, listener);
        const componentId = String(component && component.id ? component.id : "").trim();
        if (!componentId) return;
        registerComponentCleanup(componentId, () => {
          element.removeEventListener(domEvent, listener);
        });
      }

      function dispatchBoundValueEvent(component, eventType, valueBinding, value, renderContext) {
        applyValueBinding(valueBinding, value);
        dispatchComponentEvent(
          component,
          eventType,
          { value },
          { renderContext },
        );
      }

      async function readFilesWithBase64(fileList, maxBytes) {
        const out = [];
        for (const file of Array.from(fileList || [])) {
          if (file.size > maxBytes) {
            out.push({
              name: file.name,
              mime: file.type || "application/octet-stream",
              size: file.size,
              too_large: true,
            });
            continue;
          }
          const buf = await file.arrayBuffer();
          let binary = "";
          const bytes = new Uint8Array(buf);
          const chunk = 0x8000;
          for (let i = 0; i < bytes.length; i += chunk) {
            const part = bytes.subarray(i, i + chunk);
            binary += String.fromCharCode.apply(null, part);
          }
          out.push({
            name: file.name,
            mime: file.type || "application/octet-stream",
            size: file.size,
            content_base64: btoa(binary),
          });
        }
        return out;
      }

      function resolveComponentTextLabel(componentId, fallback, renderContext) {
        const component = normalizeComponent(getComponent(componentId));
        if (!component || typeof component !== "object") return String(fallback || "");
        const props = component.props || {};
        if (component.type === "Text") {
          return valueAsString(props.text, fallback || "", renderContext);
        }
        if (component.type === "Icon") {
          return valueAsString(props.name, fallback || "", renderContext);
        }
        if (component.type === "Button") {
          return valueAsString(props.label, fallback || "", renderContext);
        }
        return String(fallback || "");
      }

      function buildTemplateRenderContext(item, index, baseContext) {
        const scope = mergeObjects(
          {},
          isObjectRecord(baseContext) ? baseContext : {},
        );
        scope.item = item;
        scope.index = index;
        if (isObjectRecord(item)) {
          for (const [key, value] of Object.entries(item)) {
            if (scope[key] === undefined) {
              scope[key] = value;
            }
          }
        }
        return scope;
      }

      function resolveChildDescriptors(childrenSpec, baseContext) {
        const out = [];
        if (Array.isArray(childrenSpec)) {
          for (const childId of childrenSpec) {
            const token = String(childId || "").trim();
            if (token) {
              out.push({ componentId: token, context: baseContext });
            }
          }
          return out;
        }
        if (!isObjectRecord(childrenSpec)) {
          return out;
        }
        const templateId = String(childrenSpec.componentId || "").trim();
        const path = String(childrenSpec.path || "").trim();
        if (!templateId || !path) {
          return out;
        }
        const listValue = renderValue({ path }, baseContext);
        if (!Array.isArray(listValue)) {
          return out;
        }
        listValue.forEach((item, index) => {
          out.push({
            componentId: templateId,
            context: buildTemplateRenderContext(item, index, baseContext),
          });
        });
        return out;
      }

      function cssJustifyValue(value) {
        const token = String(value || "").trim();
        const map = {
          start: "flex-start",
          end: "flex-end",
          center: "center",
          stretch: "",
          spaceBetween: "space-between",
          spaceAround: "space-around",
          spaceEvenly: "space-evenly",
        };
        return map[token] || "";
      }

      function cssAlignValue(value) {
        const token = String(value || "").trim();
        const map = {
          start: "flex-start",
          end: "flex-end",
          center: "center",
          stretch: "stretch",
        };
        return map[token] || "";
      }

      function renderMediaComponent(type, props, componentContext, wrap) {
        if (type === "Image") {
          const img = document.createElement("img");
          img.src = valueAsString(props.url, "", componentContext);
          img.alt = "";
          img.style.maxWidth = "100%";
          img.style.borderRadius = "8px";
          const fit = String(valueAsString(props.fit, "", componentContext) || "").trim();
          const fitMap = {
            contain: "contain",
            cover: "cover",
            fill: "fill",
            none: "none",
            "scale-down": "scale-down",
          };
          if (fit && fitMap[fit]) {
            img.style.objectFit = fitMap[fit];
          }
          const variant = String(valueAsString(props.variant, "", componentContext) || "").trim();
          if (variant === "icon") {
            img.style.width = "24px";
            img.style.height = "24px";
            img.style.borderRadius = "4px";
          } else if (variant === "avatar") {
            img.style.width = "48px";
            img.style.height = "48px";
            img.style.borderRadius = "999px";
          } else if (variant === "smallFeature") {
            img.style.width = "140px";
          } else if (variant === "mediumFeature") {
            img.style.width = "220px";
          } else if (variant === "largeFeature" || variant === "header") {
            img.style.width = "100%";
          }
          wrap.appendChild(img);
          return wrap;
        }

        if (type === "Video") {
          const video = document.createElement("video");
          video.src = valueAsString(props.url, "", componentContext);
          video.controls = true;
          video.style.maxWidth = "100%";
          video.style.borderRadius = "8px";
          wrap.appendChild(video);
          return wrap;
        }

        if (type === "AudioPlayer") {
          const audio = document.createElement("audio");
          audio.src = valueAsString(props.url, "", componentContext);
          audio.controls = true;
          audio.style.width = "100%";
          wrap.appendChild(audio);
          return wrap;
        }

        if (type === "Icon") {
          const icon = document.createElement("span");
          icon.className = "small";
          icon.textContent = valueAsString(props.name, "icon");
          wrap.appendChild(icon);
          return wrap;
        }
        return null;
      }

      function renderLayoutComponent(type, props, component, componentContext, wrap) {
        if (type === "Row" || type === "Column") {
          const container = document.createElement("div");
          container.className = "container " + (type === "Row" ? "row" : "column");
          const justify = cssJustifyValue(valueAsString(props.justify, "", componentContext));
          const align = cssAlignValue(valueAsString(props.align, "", componentContext));
          if (justify) container.style.justifyContent = justify;
          if (align) container.style.alignItems = align;
          const childDescriptors = resolveChildDescriptors(props.children, componentContext);
          for (const descriptor of childDescriptors) {
            container.appendChild(renderComponent(descriptor.componentId, descriptor.context));
          }
          wrap.appendChild(container);
          return wrap;
        }

        if (type === "List") {
          const listWrap = document.createElement("div");
          const direction = valueAsString(props.direction, "vertical", componentContext);
          listWrap.className = "container " + (direction === "horizontal" ? "row" : "column");
          const align = cssAlignValue(valueAsString(props.align, "", componentContext));
          if (align) listWrap.style.alignItems = align;
          const childDescriptors = resolveChildDescriptors(props.children, componentContext);
          for (const descriptor of childDescriptors) {
            listWrap.appendChild(renderComponent(descriptor.componentId, descriptor.context));
          }
          wrap.appendChild(listWrap);
          return wrap;
        }

        if (type === "Card") {
          wrap.classList.add("card");
          const childId = String(props.child || "").trim();
          if (childId) {
            wrap.appendChild(renderComponent(childId, componentContext));
          } else {
            const empty = document.createElement("div");
            empty.className = "small";
            empty.textContent = "Card child is missing.";
            wrap.appendChild(empty);
          }
          return wrap;
        }

        if (type === "Tabs") {
          const tabs = Array.isArray(props.tabs) ? props.tabs : [];
          if (!tabs.length) {
            const empty = document.createElement("div");
            empty.className = "small";
            empty.textContent = "Tabs has no items.";
            wrap.appendChild(empty);
            return wrap;
          }
          const tabBar = document.createElement("div");
          tabBar.className = "action-bar";
          const body = document.createElement("div");
          let activeIndex = 0;
          const tabButtons = [];
          const tabPanels = [];

          const syncTabVisibility = () => {
            for (let i = 0; i < tabButtons.length; i += 1) {
              tabButtons[i].className = i === activeIndex ? "primary" : "secondary";
            }
            for (let i = 0; i < tabPanels.length; i += 1) {
              tabPanels[i].style.display = i === activeIndex ? "" : "none";
            }
          };

          tabs.forEach((tab, index) => {
            if (!tab || typeof tab !== "object") return;
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = index === activeIndex ? "primary" : "secondary";
            btn.textContent = valueAsString(tab.title, "Tab", componentContext);
            const onTabClick = () => {
              activeIndex = index;
              dispatchComponentEvent(
                component,
                "change",
                { index, title: tab.title, child: tab.child },
                {
                  fallbackLabel: tab.title || "tab",
                  renderContext: componentContext,
                },
              );
              syncTabVisibility();
            };
            attachComponentListener(component, btn, "click", onTabClick);
            tabButtons.push(btn);
            tabBar.appendChild(btn);

            const panel = document.createElement("div");
            panel.style.display = index === activeIndex ? "" : "none";
            panel.appendChild(renderComponent(String(tab.child || ""), componentContext));
            tabPanels.push(panel);
            body.appendChild(panel);
          });

          wrap.appendChild(tabBar);
          wrap.appendChild(body);
          syncTabVisibility();
          return wrap;
        }

        if (type === "Modal") {
          const triggerId = String(props.trigger || "").trim();
          const contentId = String(props.content || "").trim();
          const triggerButton = document.createElement("button");
          triggerButton.type = "button";
          triggerButton.className = "secondary";
          triggerButton.textContent = resolveComponentTextLabel(triggerId, "Open", componentContext);
          wrap.appendChild(triggerButton);

          const modalBody = document.createElement("div");
          modalBody.className = "card";
          modalBody.style.display = "none";
          modalBody.style.marginTop = "8px";
          modalBody.appendChild(renderComponent(contentId, componentContext));
          const closeButton = document.createElement("button");
          closeButton.type = "button";
          closeButton.className = "secondary";
          closeButton.textContent = "Close";
          closeButton.style.marginTop = "8px";
          modalBody.appendChild(closeButton);
          wrap.appendChild(modalBody);

          const onOpen = () => {
            modalBody.style.display = "block";
            dispatchComponentEvent(
              component,
              "open",
              { trigger: triggerId, content: contentId },
              { renderContext: componentContext },
            );
          };
          const onClose = () => {
            modalBody.style.display = "none";
            dispatchComponentEvent(
              component,
              "close",
              { trigger: triggerId, content: contentId },
              { renderContext: componentContext },
            );
          };
          attachComponentListener(component, triggerButton, "click", onOpen);
          attachComponentListener(component, closeButton, "click", onClose);
          return wrap;
        }

        if (type === "Divider") {
          const hrWrap = document.createElement("div");
          const axis = String(valueAsString(props.axis, "horizontal", componentContext) || "horizontal").trim();
          const hr = document.createElement("hr");
          if (axis === "vertical") {
            hr.style.border = "none";
            hr.style.borderLeft = "1px solid var(--border)";
            hr.style.height = "100%";
            hr.style.minHeight = "20px";
            hr.style.margin = "0 8px";
            hrWrap.style.display = "inline-flex";
            hrWrap.style.alignItems = "stretch";
          } else {
            hr.style.border = "none";
            hr.style.borderTop = "1px solid var(--border)";
            hr.style.margin = "8px 0";
          }
          hrWrap.appendChild(hr);
          wrap.appendChild(hrWrap);
          return wrap;
        }
        return null;
      }

      function renderInputComponent(type, props, component, componentContext, wrap) {
        if (type === "Button") {
          const button = document.createElement("button");
          button.type = "button";
          button.className = String(props.variant || "") === "primary" ? "primary" : "secondary";
          const fallbackLabel = props.child
            ? resolveComponentTextLabel(props.child, "Action", componentContext)
            : "Action";
          button.textContent = valueAsString(props.label, fallbackLabel, componentContext);
          attachComponentListener(component, button, "click", () => {
            dispatchComponentEvent(
              component,
              "click",
              {},
              { renderContext: componentContext },
            );
          });
          wrap.appendChild(button);
          return wrap;
        }

        if (type === "TextField") {
          const field = document.createElement("div");
          field.className = "field";
          const label = document.createElement("label");
          label.textContent = valueAsString(props.label, "Input", componentContext);
          field.appendChild(label);

          const variant = String(props.variant || "shortText");
          const input = variant === "longText" ? document.createElement("textarea") : document.createElement("input");
          if (variant === "number") input.type = "number";
          else if (variant === "obscured") input.type = "password";
          else if (variant !== "longText") input.type = "text";

          const resolvedValue = renderValue(props.value, componentContext);
          if (resolvedValue !== undefined && resolvedValue !== null) {
            input.value = String(resolvedValue);
          }
          if (props.placeholder) input.placeholder = valueAsString(props.placeholder, "", componentContext);

          // Keep bound state hot while typing so button actions reading /state
          // are not dependent on browser-specific change/blur event ordering.
          const syncBoundValue = () => {
            applyValueBinding(props.value, input.value);
          };
          attachComponentListener(component, input, "input", () => {
            syncBoundValue();
          });
          attachComponentListener(component, input, "change", () => {
            syncBoundValue();
            dispatchComponentEvent(
              component,
              "change",
              { value: input.value },
              { renderContext: componentContext },
            );
          });
          attachComponentListener(component, input, "keydown", (evt) => {
            if (evt.key === "Enter") {
              syncBoundValue();
              dispatchComponentEvent(
                component,
                "submit",
                { value: input.value },
                { renderContext: componentContext },
              );
            }
          });
          field.appendChild(input);
          wrap.appendChild(field);
          return wrap;
        }

        if (type === "CheckBox") {
          const row = document.createElement("label");
          row.style.display = "flex";
          row.style.alignItems = "center";
          row.style.gap = "8px";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = valueAsBoolean(props.value, false, componentContext);
          attachComponentListener(component, checkbox, "change", () => {
            dispatchBoundValueEvent(component, "change", props.value, checkbox.checked, componentContext);
          });
          row.appendChild(checkbox);
          const text = document.createElement("span");
          text.textContent = valueAsString(props.label, "Check", componentContext);
          row.appendChild(text);
          wrap.appendChild(row);
          return wrap;
        }

        if (type === "ChoicePicker") {
          const field = document.createElement("div");
          field.className = "field";
          const label = document.createElement("label");
          label.textContent = valueAsString(props.label, "Choice", componentContext);
          field.appendChild(label);
          const options = normalizeOptionList(props.options);
          const variant = String(props.variant || "mutuallyExclusive");
          if (variant === "multipleSelection") {
            const selectedValue = renderValue(props.value, componentContext);
            const selected = Array.isArray(selectedValue) ? selectedValue.map((item) => String(item)) : [];
            options.forEach((option) => {
              const row = document.createElement("label");
              row.style.display = "flex";
              row.style.alignItems = "center";
              row.style.gap = "8px";
              const input = document.createElement("input");
              input.type = "checkbox";
              input.value = option.value;
              input.checked = selected.includes(option.value);
              attachComponentListener(component, input, "change", () => {
                const next = Array.from(field.querySelectorAll("input[type='checkbox']"))
                  .filter((item) => item.checked)
                  .map((item) => String(item.value));
                dispatchBoundValueEvent(component, "change", props.value, next, componentContext);
              });
              row.appendChild(input);
              const text = document.createElement("span");
              text.textContent = option.label;
              row.appendChild(text);
              field.appendChild(row);
            });
          } else {
            const select = document.createElement("select");
            const selected = valueAsString(props.value, "", componentContext);
            for (const option of options) {
              const opt = document.createElement("option");
              opt.value = option.value;
              opt.textContent = option.label;
              if (selected === option.value) opt.selected = true;
              select.appendChild(opt);
            }
            attachComponentListener(component, select, "change", () => {
              dispatchBoundValueEvent(component, "change", props.value, select.value, componentContext);
            });
            field.appendChild(select);
          }
          wrap.appendChild(field);
          return wrap;
        }

        if (type === "Slider") {
          const field = document.createElement("div");
          field.className = "field";
          const label = document.createElement("label");
          label.textContent = valueAsString(props.label, "Value", componentContext);
          field.appendChild(label);

          const input = document.createElement("input");
          input.type = "range";
          input.min = valueAsString(props.min, "0", componentContext);
          input.max = valueAsString(props.max, "100", componentContext);
          input.step = valueAsString(props.step, "1", componentContext);
          input.value = valueAsString(props.value, input.min, componentContext);
          const readout = document.createElement("div");
          readout.className = "small";
          readout.textContent = input.value;
          attachComponentListener(component, input, "input", () => {
            readout.textContent = input.value;
          });
          attachComponentListener(component, input, "change", () => {
            const numeric = Number(input.value);
            dispatchBoundValueEvent(
              component,
              "change",
              props.value,
              Number.isFinite(numeric) ? numeric : input.value,
              componentContext,
            );
          });
          field.appendChild(input);
          field.appendChild(readout);
          wrap.appendChild(field);
          return wrap;
        }

        if (type === "DateTimeInput") {
          const field = document.createElement("div");
          field.className = "field";
          const label = document.createElement("label");
          label.textContent = valueAsString(props.label, "Date/Time", componentContext);
          field.appendChild(label);
          const input = document.createElement("input");
          const enableDate = valueAsBoolean(props.enableDate, true, componentContext);
          const enableTime = valueAsBoolean(props.enableTime, false, componentContext);
          input.type = enableDate && enableTime ? "datetime-local" : (enableTime ? "time" : "date");
          input.value = valueAsString(props.value, "", componentContext);
          if (props.min) input.min = valueAsString(props.min, "", componentContext);
          if (props.max) input.max = valueAsString(props.max, "", componentContext);
          attachComponentListener(component, input, "change", () => {
            dispatchBoundValueEvent(component, "change", props.value, input.value, componentContext);
          });
          field.appendChild(input);
          wrap.appendChild(field);
          return wrap;
        }

        return null;
      }

      function renderComponent(componentId, renderContext) {
        const component = normalizeComponent(getComponent(componentId));
        if (!component) {
          const missing = document.createElement("div");
          missing.className = "component card error";
          missing.textContent = "Missing component: " + componentId;
          return missing;
        }

        const type = component.type;
        const props = component.props || {};
        const componentContext = isObjectRecord(renderContext)
          ? mergeObjects({}, renderContext)
          : {};
        const wrap = document.createElement("div");
        wrap.className = "component";
        wrap.dataset.componentId = component.id;

        if (props.title) {
          const title = document.createElement("div");
          title.className = "component-title";
          title.textContent = valueAsString(props.title, "", componentContext);
          wrap.appendChild(title);
        }

        if (type === "Text") {
          const p = document.createElement("div");
          p.className = "text";
          const variant = String(valueAsString(props.variant, "body", componentContext) || "body").trim();
          if (variant) {
            p.classList.add("variant-" + variant);
          }
          p.textContent = valueAsString(props.text, "", componentContext);
          wrap.appendChild(p);
          return wrap;
        }

        const layout = renderLayoutComponent(type, props, component, componentContext, wrap);
        if (layout) {
          return layout;
        }

        const input = renderInputComponent(type, props, component, componentContext, wrap);
        if (input) {
          return input;
        }

        const media = renderMediaComponent(type, props, componentContext, wrap);
        if (media) {
          return media;
        }

        const fallback = document.createElement("div");
        fallback.className = "fallback";
        const hint = document.createElement("div");
        hint.className = "small";
        hint.textContent = "Unsupported component type: " + String(type || "unknown");
        fallback.appendChild(hint);
        const details = document.createElement("pre");
        details.textContent = JSON.stringify(component, null, 2);
        fallback.appendChild(details);
        wrap.appendChild(fallback);
        return wrap;
      }

      function sanitizeSpecForRender(spec) {
        const next = mergeObjects({}, spec || {});
        next.components = Array.isArray(next.components)
          ? next.components.map((component) => normalizeComponent(component))
          : [];
        const ids = new Set();
        for (const component of next.components) {
          if (component && typeof component.id === "string" && component.id.trim()) {
            ids.add(component.id.trim());
          }
        }
        const rawRoot = Array.isArray(next.root) ? next.root : [];
        const root = [];
        for (const id of rawRoot) {
          if (ids.has(id) && !root.includes(id)) root.push(id);
        }
        if (!root.length) {
          throw new Error("Spec root must reference existing component ids.");
        }
        next.root = root;
        return next;
      }

      function rebuildComponentIndex(spec) {
        appState.componentById = {};
        for (const component of spec.components || []) {
          appState.componentById[component.id] = component;
        }
      }

      function renderSpec(spec) {
        const sanitizedSpec = sanitizeSpecForRender(spec);
        appState.spec = sanitizedSpec;
        const resolvedSpec = applyStateBindings(sanitizedSpec, appState.state);
        applyTheme(resolvedSpec.theme || {});
        titleEl.textContent = valueAsString(resolvedSpec.title, "MetaUI");
        rebuildComponentIndex(resolvedSpec);

        const previousCleanupById = appState.componentCleanupById || {};
        appState.componentCleanupById = {};
        const fragment = document.createDocumentFragment();
        for (const rootId of resolvedSpec.root || []) {
          try {
            fragment.appendChild(renderComponent(rootId));
          } catch (err) {
            console.error("MetaUI render error:", rootId, err);
            const errDiv = document.createElement("div");
            errDiv.style.cssText = "padding:16px;color:#d32f2f;font-size:15px;border:1px solid #d32f2f;border-radius:6px;margin:8px 0";
            errDiv.textContent = "Render error (" + rootId + "): " + String(err.message || err);
            fragment.appendChild(errDiv);
          }
        }
        if (!fragment.childNodes.length) {
          const empty = document.createElement("div");
          empty.className = "small";
          empty.textContent = "No renderable components in current UI spec.";
          fragment.appendChild(empty);
        }
        contentEl.innerHTML = "";
        contentEl.appendChild(fragment);
        releaseComponentCleanupMap(previousCleanupById);
      }
