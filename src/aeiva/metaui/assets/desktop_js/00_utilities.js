      function isObjectRecord(value) {
        return Boolean(value) && typeof value === "object" && !Array.isArray(value);
      }

      function mergeObjects(target, source) {
        const out = Object.assign({}, target || {});
        for (const [key, value] of Object.entries(source || {})) {
          if (isObjectRecord(value)) {
            out[key] = mergeObjects(out[key], value);
          } else {
            out[key] = value;
          }
        }
        return out;
      }

      function normalizeToken(value) {
        return String(value || "")
          .trim()
          .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "_")
          .replace(/_{2,}/g, "_")
          .replace(/^_+|_+$/g, "");
      }

      function normalizeTheme(theme) {
        if (!isObjectRecord(theme)) return {};
        const out = {};
        for (const [rawKey, rawValue] of Object.entries(theme)) {
          const token = String(rawKey || "").trim();
          if (!token) continue;
          if (rawValue === null || rawValue === undefined) continue;
          if (typeof rawValue === "number" && Number.isFinite(rawValue)) {
            out[token] = rawValue;
            continue;
          }
          out[token] = String(rawValue);
        }
        return out;
      }

      function toFiniteNumber(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
      }
