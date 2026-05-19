(function () {
  "use strict";

  var HEX6 = /^#[0-9a-fA-F]{6}$/;
  var HEX3 = /^#[0-9a-fA-F]{3}$/;

  function expandHex3(hex) {
    if (!HEX3.test(hex)) {
      return null;
    }
    var h = hex.slice(1);
    return (
      "#" +
      h[0] +
      h[0] +
      h[1] +
      h[1] +
      h[2] +
      h[2]
    ).toLowerCase();
  }

  function normalizeHex(raw) {
    var s = (raw || "").trim();
    if (!s) {
      return null;
    }
    if (!s.startsWith("#")) {
      s = "#" + s;
    }
    if (HEX3.test(s)) {
      return expandHex3(s);
    }
    if (HEX6.test(s)) {
      return s.toLowerCase();
    }
    return null;
  }

  function pickerValue(hex) {
    return normalizeHex(hex) || "#000000";
  }

  function setInvalid(textInput, invalid) {
    textInput.classList.toggle("hex-color-text--invalid", invalid);
  }

  function updateSwatch(container, hex) {
    var swatch = container.querySelector(".hex-color-swatch");
    var picker = container.querySelector(".hex-color-picker");
    var value = pickerValue(hex);
    if (swatch) {
      swatch.style.backgroundColor = value;
    }
    if (picker) {
      picker.value = value;
    }
  }

  function bindWidget(container) {
    if (container.dataset.hexColorBound === "1") {
      return;
    }
    container.dataset.hexColorBound = "1";

    var text = container.querySelector(".hex-color-text");
    var picker = container.querySelector(".hex-color-picker");
    var swatch = container.querySelector(".hex-color-swatch");
    if (!text || !picker) {
      return;
    }

    updateSwatch(container, text.value);

    picker.addEventListener("input", function () {
      var hex = picker.value.toLowerCase();
      text.value = hex;
      setInvalid(text, false);
      if (swatch) {
        swatch.style.backgroundColor = hex;
      }
    });

    text.addEventListener("input", function () {
      var normalized = normalizeHex(text.value);
      setInvalid(text, text.value.trim() !== "" && !normalized);
      if (normalized) {
        updateSwatch(container, normalized);
      }
    });

    text.addEventListener("blur", function () {
      var normalized = normalizeHex(text.value);
      if (normalized) {
        text.value = normalized;
        setInvalid(text, false);
        updateSwatch(container, normalized);
      } else if (text.value.trim() === "") {
        setInvalid(text, false);
      } else {
        setInvalid(text, true);
      }
    });

    if (swatch) {
      swatch.addEventListener("click", function () {
        picker.click();
      });
    }
  }

  function wrapPlainColorInput(input) {
    if (
      input.classList.contains("hex-color-text") ||
      input.closest("[data-hex-color-widget]")
    ) {
      return;
    }
    var name = input.getAttribute("name") || "";
    if (!/-color$/.test(name) && name !== "color") {
      return;
    }

    var wrapper = document.createElement("div");
    wrapper.className = "hex-color-widget";
    wrapper.setAttribute("data-hex-color-widget", "");

    var swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = "hex-color-swatch";
    swatch.setAttribute("aria-label", "Pick color");

    var picker = document.createElement("input");
    picker.type = "color";
    picker.className = "hex-color-picker";
    picker.tabIndex = -1;
    picker.setAttribute("aria-hidden", "true");

    input.classList.add("hex-color-text");
    input.setAttribute("maxlength", "7");
    input.setAttribute("placeholder", "#RRGGBB");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("spellcheck", "false");

    var parent = input.parentNode;
    parent.insertBefore(wrapper, input);
    wrapper.appendChild(swatch);
    wrapper.appendChild(picker);
    wrapper.appendChild(input);

    bindWidget(wrapper);
  }

  function initHexColorInputs(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll("[data-hex-color-widget]").forEach(bindWidget);
    scope.querySelectorAll('input[name$="-color"], input[name="color"]').forEach(
      wrapPlainColorInput
    );
  }

  window.hexColorNormalize = normalizeHex;
  window.initHexColorInputs = initHexColorInputs;

  function observeDynamicWidgets() {
    if (!document.body || typeof MutationObserver === "undefined") {
      return;
    }
    var observer = new MutationObserver(function () {
      initHexColorInputs(document);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function onReady() {
    initHexColorInputs(document);
    observeDynamicWidgets();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }

  document.addEventListener("w-formset:added", function (event) {
    var row = event.detail && event.detail.row;
    initHexColorInputs(row || document);
  });

  document.addEventListener("w-swap:success", function (event) {
    var root = (event.target && event.target.querySelector)
      ? event.target
      : document;
    initHexColorInputs(root);
  });
})();
