/**
 * QIQ Widget — Embed Script
 *
 * Add one <div> per widget and a single <script> tag anywhere on the page:
 *
 *   <div data-qiq-widget
 *        data-api-base="https://your-api.com"
 *        data-calendly-url="https://calendly.com/your-link"
 *        data-pathway="portugal_d7"
 *        data-company-name="Great Expatations">
 *   </div>
 *   <script src="https://your-host/widget/embed.js"></script>
 *
 * Multiple [data-qiq-widget] elements on the same page are supported — each
 * reads its own data attributes and gets isolated element refs via data-qiq-ref.
 */
(function () {
  "use strict";

  console.log('[QIQ embed] Script loaded, readyState:', document.readyState);

  // Capture currentScript synchronously — needed for baseUrl(), null once IIFE returns
  var SCRIPT_EL = document.currentScript;

  // ── Widget HTML template ────────────────────────────────────────────────────
  var WIDGET_HTML = [
    // Layer 1
    '<div class="qiq-layer qiq-layer-1 active">',
    '  <div class="qiq-intro">',
    '    <h3>Check Your Visa<br>Eligibility in 1 Minute</h3>',
    '    <p>Simply enter your name and email to get started</p>',
    '  </div>',
    '  <form class="qiq-form" onsubmit="return false">',
    '    <div class="qiq-field" data-qiq-ref="name-field">',
    '      <label>Your name</label>',
    '      <input data-qiq-ref="name" type="text" placeholder="Your name" autocomplete="name" spellcheck="false" />',
    '      <span class="field-error"></span>',
    '    </div>',
    '    <div class="qiq-field" data-qiq-ref="email-field">',
    '      <label>Email address</label>',
    '      <input data-qiq-ref="email" type="email" placeholder="Your email address" autocomplete="email" spellcheck="false" />',
    '      <span class="field-error"></span>',
    '    </div>',
    '    <button data-qiq-ref="submit" class="qiq-btn-primary" type="button">Submit</button>',
    '  </form>',
    '  <div class="qiq-badge">',
    '    <span class="qiq-badge-check">&#10003;</span>',
    '    <span>2000+ VISAS APPROVED WITH ROOTS GLOBAL</span>',
    '  </div>',
    '</div>',
    // Layer 2
    '<div class="qiq-layer qiq-layer-2">',
    '  <div class="qiq-chat-messages"></div>',
    '  <div class="qiq-chat-input-row">',
    '    <input data-qiq-ref="chat-input" class="qiq-chat-input" type="text" placeholder="Type your answer&hellip;" autocomplete="off" />',
    '    <button data-qiq-ref="send-btn" class="qiq-chat-send" aria-label="Send">',
    '      <svg width="18" height="18" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
    '    </button>',
    '  </div>',
    '</div>',
    // Layer 3
    '<div class="qiq-layer qiq-layer-3">',
    '  <div class="qiq-result-content"></div>',
    '  <div class="qiq-result-footer">',
    '    <div class="qiq-result-actions">',
    '      <a data-qiq-ref="pdf-btn" class="qiq-btn-dark" href="#" target="_blank" rel="noopener">Download PDF</a>',
    '      <a data-qiq-ref="call-btn" class="qiq-btn-dark" href="#" target="_blank" rel="noopener">Book a Call</a>',
    '    </div>',
    '  </div>',
    '</div>',
  ].join("\n");

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function baseUrl() {
    // Derive asset root from this script's own src URL
    var src = (SCRIPT_EL && SCRIPT_EL.src) || "";
    return src.substring(0, src.lastIndexOf("/") + 1);
  }

  function injectCSS(base) {
    if (document.querySelector("[data-qiq-css]")) return; // already loaded
    var link = document.createElement("link");
    link.rel  = "stylesheet";
    link.href = base + "widget.css";
    link.setAttribute("data-qiq-css", "1");
    document.head.appendChild(link);
  }

  function loadJS(base, callback) {
    if (window.QIQWidget) { callback(); return; } // already loaded
    var s    = document.createElement("script");
    s.src    = base + "widget.js";
    s.async  = true;
    s.onload = callback;
    document.head.appendChild(s);
  }

  function initWidget(el) {
    var apiBase     = el.getAttribute("data-api-base")     || "";
    var calendlyUrl = el.getAttribute("data-calendly-url") || "#";
    var pathway     = el.getAttribute("data-pathway")      || null;
    var companyName = el.getAttribute("data-company-name") || "";

    el.classList.add("qiq-widget");
    el.innerHTML = WIDGET_HTML;

    new window.QIQWidget(el, {
      apiBase:     apiBase,
      calendlyUrl: calendlyUrl,
      pathway:     pathway,
      companyName: companyName,
    });
  }

  // ── Main init ───────────────────────────────────────────────────────────────

  function init() {
    var base    = baseUrl();
    var targets = document.querySelectorAll("[data-qiq-widget]");
    console.log('[QIQ embed] init() called, base:', base);
    console.log('[QIQ embed] found', targets.length, 'widget target(s)');

    if (!targets.length) return;

    injectCSS(base);
    console.log('[QIQ embed] CSS injected');

    loadJS(base, function () {
      console.log('[QIQ embed] widget.js loaded, QIQWidget:', window.QIQWidget);
      for (var i = 0; i < targets.length; i++) {
        initWidget(targets[i]);
      }
    });
  }

  // Run after DOM is ready (handles both sync and async/defer loading)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
