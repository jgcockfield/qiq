/**
 * QIQ Widget — Embed Script
 *
 * Drop this ONE tag anywhere on a client page:
 *
 *   <script src="https://your-host/widget/embed.js"
 *           data-api-base="https://your-api.com"
 *           data-calendly-url="https://calendly.com/your-link"
 *           data-pathway="portugal_d7"
 *           data-company-name="Great Expatations">
 *   </script>
 *
 * Optional: target an existing element instead of auto-inserting:
 *           data-container="#my-div"
 *
 * Multiple instances on the same page are supported — each gets isolated
 * element refs via data-qiq-ref scoped to its root element.
 */
(function () {
  "use strict";

  console.log('[QIQ embed] Script loaded, readyState:', document.readyState);

  // Capture currentScript synchronously — it's null once the IIFE returns
  var SCRIPT_EL = document.currentScript;

  // ── Widget HTML template ────────────────────────────────────────────────────
  // data-qiq-ref attributes are the binding points; no id= collisions between
  // multiple instances on the same page.
  var WIDGET_HTML = [
    '<div class="qiq-header">',
    '  <div class="qiq-header-logo">Q</div>',
    '  <div class="qiq-header-text">',
    '    <h2>QualifyIQ</h2>',
    '    <p>Check your eligibility in minutes</p>',
    '  </div>',
    '</div>',
    '<div class="qiq-progress">',
    '  <div class="qiq-progress-bar" style="width:10%"></div>',
    '</div>',
    // Layer 1
    '<div class="qiq-layer qiq-layer-1 active">',
    '  <div class="qiq-intro">',
    '    <h3>Let\'s check your eligibility</h3>',
    '    <p>Answer a few quick questions and we\'ll tell you where you stand &mdash; no commitment required.</p>',
    '  </div>',
    '  <form class="qiq-form" onsubmit="return false">',
    '    <div class="qiq-field" data-qiq-ref="name-field">',
    '      <label>Your name</label>',
    '      <input data-qiq-ref="name" type="text" placeholder="Jane Smith" autocomplete="name" spellcheck="false" />',
    '      <span class="field-error"></span>',
    '    </div>',
    '    <div class="qiq-field" data-qiq-ref="email-field">',
    '      <label>Email address</label>',
    '      <input data-qiq-ref="email" type="email" placeholder="jane@example.com" autocomplete="email" spellcheck="false" />',
    '      <span class="field-error"></span>',
    '    </div>',
    '    <button data-qiq-ref="submit" class="qiq-btn-primary" type="button">Start my assessment &rarr;</button>',
    '  </form>',
    '  <p class="qiq-disclaimer">Your information is only used to personalise your results. We don\'t share it with third parties.</p>',
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
    '    <p>If you would like assistance addressing the pending requirements, professional support is available.</p>',
    '    <p>Services may include document review, application preparation, and legal consultation.</p>',
    '    <a data-qiq-ref="call-link" class="qiq-book-consult-link" href="#" target="_blank" rel="noopener">',
    '      Book a consultation with <span class="qiq-company-name">us</span>',
    '    </a>',
    '    <div class="qiq-result-actions">',
    '      <a data-qiq-ref="pdf-btn" class="qiq-btn-dark" href="#" target="_blank" rel="noopener">Download PDF</a>',
    '      <a data-qiq-ref="call-btn" class="qiq-btn-dark" href="#" target="_blank" rel="noopener">Book a Call</a>',
    '    </div>',
    '  </div>',
    '</div>',
  ].join("\n");

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function attr(name, fallback) {
    return (SCRIPT_EL && SCRIPT_EL.getAttribute(name)) || fallback;
  }

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

  // ── Main init ───────────────────────────────────────────────────────────────

  function init() {
    var base        = baseUrl();
    console.log('[QIQ embed] init() called, base:', base);
    var apiBase     = attr("data-api-base",     "");
    var calendlyUrl = attr("data-calendly-url", "#");
    var pathway     = attr("data-pathway",      null);
    var companyName = attr("data-company-name", "");
    var container   = attr("data-container",    null);

    injectCSS(base);
    console.log('[QIQ embed] CSS injected');

    // Build the widget root element
    var widget       = document.createElement("div");
    widget.className = "qiq-widget";
    widget.innerHTML = WIDGET_HTML;

    // Insert into specified container or directly after the script tag
    if (container) {
      var target = document.querySelector(container);
      if (target) { target.appendChild(widget); }
      else { console.warn("[QIQ embed] container not found:", container); return; }
    } else {
      SCRIPT_EL.parentNode.insertBefore(widget, SCRIPT_EL.nextSibling);
    }

    // Load widget.js and initialize
    loadJS(base, function () {
      console.log('[QIQ embed] widget.js loaded, QIQWidget:', window.QIQWidget);
      new window.QIQWidget(widget, {
        apiBase:     apiBase,
        calendlyUrl: calendlyUrl,
        pathway:     pathway,
        companyName: companyName,
      });
    });
  }

  // Run after DOM is ready (handles both sync and async/defer loading)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
