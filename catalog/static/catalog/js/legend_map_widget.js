(function () {
  "use strict";
  if (window.__legendMapWidgetLoaded) return;
  window.__legendMapWidgetLoaded = true;

  function normalizeHex(raw) {
    if (typeof window.hexColorNormalize === "function") {
      return window.hexColorNormalize(raw);
    }
    var s = (raw || "").trim();
    if (!s) return null;
    if (s.charAt(0) !== "#") s = "#" + s;
    if (/^#[0-9a-fA-F]{6}$/.test(s)) return s.toLowerCase();
    return null;
  }

  function serializeSimple(container) {
    var hidden = container.querySelector(".legend-map-json-hidden");
    if (!hidden) return;
    var rows = container.querySelectorAll("[data-legend-map-row]");
    var obj = {};
    rows.forEach(function (row) {
      var nameEl = row.querySelector(".legend-map-name");
      var colorEl = row.querySelector(".hex-color-text");
      if (!nameEl || !colorEl) return;
      var name = nameEl.value.trim();
      var color = normalizeHex(colorEl.value);
      if (name && color) {
        obj[name] = color;
      }
    });
    hidden.value = JSON.stringify(obj);
  }

  function useAdvancedMode(container) {
    return container.getAttribute("data-advanced-mode") === "1";
  }

  function serializeAdvanced(container) {
    var hidden = container.querySelector(".legend-map-json-hidden");
    var raw = container.querySelector(".legend-map-json-raw");
    if (!hidden || !raw) return;
    raw.classList.remove("legend-map-json-raw--invalid");
    try {
      var parsed = JSON.parse(raw.value || "{}");
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("Legend must be a JSON object");
      }
      hidden.value = JSON.stringify(parsed);
    } catch (e) {
      raw.classList.add("legend-map-json-raw--invalid");
    }
  }

  function syncHidden(container) {
    if (useAdvancedMode(container)) {
      serializeAdvanced(container);
    } else {
      serializeSimple(container);
    }
  }

  function addRow(container) {
    var template = container.querySelector("[data-legend-map-template]");
    var rows = container.querySelector("[data-legend-map-rows]");
    if (!template || !rows) return;
    var source =
      template.content.querySelector("[data-legend-map-row]") ||
      template.content.firstElementChild;
    if (!source) return;
    var row = source.cloneNode(true);
    rows.appendChild(row);
    if (typeof window.initHexColorInputs === "function") {
      window.initHexColorInputs(row);
    }
    syncHidden(container);
  }

  function removeRow(row, container) {
    var rows = container.querySelectorAll("[data-legend-map-row]");
    if (rows.length <= 1) {
      var nameEl = row.querySelector(".legend-map-name");
      if (nameEl) nameEl.value = "";
      var colorEl = row.querySelector(".hex-color-text");
      if (colorEl) {
        colorEl.value = "#000000";
        if (typeof window.initHexColorInputs === "function") {
          window.initHexColorInputs(row);
        }
      }
    } else {
      row.remove();
    }
    syncHidden(container);
  }

  function bindWidget(container) {
    if (container.dataset.legendMapBound === "1") {
      return;
    }
    container.dataset.legendMapBound = "1";

    container.addEventListener("input", function (event) {
      if (
        event.target.closest(".legend-map-name") ||
        event.target.closest(".hex-color-text")
      ) {
        syncHidden(container);
      }
    });

    container.addEventListener("change", function (event) {
      if (event.target.closest(".hex-color-picker")) {
        syncHidden(container);
      }
    });

    var raw = container.querySelector(".legend-map-json-raw");
    if (raw) {
      raw.addEventListener("input", function () {
        serializeAdvanced(container);
      });
    }

    var form = container.closest("form");
    if (form && !form.dataset.legendMapSubmitBound) {
      form.dataset.legendMapSubmitBound = "1";
      form.addEventListener("submit", function () {
        form.querySelectorAll("[data-legend-map-widget]").forEach(syncHidden);
      });
    }

    if (typeof window.initHexColorInputs === "function") {
      window.initHexColorInputs(container);
    }
    syncHidden(container);
  }

  function ensureBound(container) {
    if (!container) return;
    bindWidget(container);
  }

  function initLegendMapWidgets(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll("[data-legend-map-widget]").forEach(bindWidget);
  }

  window.initLegendMapWidgets = initLegendMapWidgets;

  window.legendMapAddRow = function (event) {
    var btn = event.currentTarget || event.target;
    var container = btn && btn.closest("[data-legend-map-widget]");
    if (!container) return;
    if (event.preventDefault) event.preventDefault();
    if (event.stopPropagation) event.stopPropagation();
    ensureBound(container);
    addRow(container);
  };

  window.legendMapRemoveRow = function (event) {
    var btn = event.currentTarget || event.target;
    var container = btn && btn.closest("[data-legend-map-widget]");
    var row = btn && btn.closest("[data-legend-map-row]");
    if (!container || !row) return;
    if (event.preventDefault) event.preventDefault();
    if (event.stopPropagation) event.stopPropagation();
    ensureBound(container);
    removeRow(row, container);
  };

  document.addEventListener(
    "click",
    function (event) {
      var addBtn = event.target.closest(".legend-map-add");
      if (addBtn) {
        var container = addBtn.closest("[data-legend-map-widget]");
        if (container) {
          event.preventDefault();
          event.stopPropagation();
          ensureBound(container);
          addRow(container);
        }
        return;
      }
      var removeBtn = event.target.closest(".legend-map-remove");
      if (removeBtn) {
        var containerRemove = removeBtn.closest("[data-legend-map-widget]");
        var row = removeBtn.closest("[data-legend-map-row]");
        if (containerRemove && row) {
          event.preventDefault();
          event.stopPropagation();
          ensureBound(containerRemove);
          removeRow(row, containerRemove);
        }
      }
    },
    true
  );

  var observerScheduled = false;
  function scheduleInit() {
    if (observerScheduled) return;
    observerScheduled = true;
    requestAnimationFrame(function () {
      observerScheduled = false;
      initLegendMapWidgets(document);
    });
  }

  function observeDynamicWidgets() {
    if (!document.body || typeof MutationObserver === "undefined") {
      return;
    }
    var observer = new MutationObserver(scheduleInit);
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function onReady() {
    initLegendMapWidgets(document);
    observeDynamicWidgets();
    scheduleInit();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }

  document.addEventListener("w-formset:added", function (event) {
    var row = event.detail && event.detail.row;
    initLegendMapWidgets(row || document);
  });

  document.addEventListener("w-swap:success", function () {
    scheduleInit();
  });
})();
