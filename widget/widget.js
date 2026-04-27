/**
 * QIQ Inline Chat Widget
 * Layers: 1 = Email Capture, 2 = Guided Dialog, 3 = Results
 */

// ── Choice label formatter ────────────────────────────────────────────────────
function _qiqDisplayChoiceLabel(v) {
  return String(v ?? "")
    .replaceAll("_", " ")
    .replaceAll(/\s+/g, " ")
    .trim()
    .split(" ")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

// ── UUID helper (crypto.randomUUID with legacy fallback) ──────────────────────
function _qiqUUID() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

class QIQWidget {
  constructor(rootEl, options = {}) {
    this.root = rootEl;
    this.opts = {
      apiBase:     options.apiBase     || "",
      calendlyUrl: options.calendlyUrl || "#",
      pathway:     options.pathway     || null,
      companyName: options.companyName || "",
    };

    // Unique per widget instance — not per page load, not tied to email.
    this.instanceId = _qiqUUID();

    // State
    this.session = { name: "", email: "" };
    // Nested payload state: answers are stored at their dotted-key paths.
    // e.g. "routing.work_relationship" -> this.answers.routing.work_relationship
    this.answers = {};
    this.currentLayer = 1;
    this.isWaiting = false;
    this._pendingFieldKey  = null;
    this._pendingInputType = "text";

    this._log("init", { instanceId: this.instanceId, opts: this.opts });

    this._bindElements();
    this._showLayer(1);
  }

  // ── Logging ───────────────────────────────────────────────────

  _log(event, data) {
    const prefix = `[QIQ:${this.instanceId.slice(0, 8)}]`;
    console.groupCollapsed(`${prefix} ${event}`);
    if (data !== undefined) console.log(data);
    console.groupEnd();
  }

  _logRequest(payload) {
    console.group(`[QIQ:${this.instanceId.slice(0, 8)}] -> POST /evaluate`);
    console.log("session_id:", payload.session_id);
    console.log("pathway:",    payload.pathway ?? "(none)");
    console.log("answers:",    JSON.parse(JSON.stringify(this.answers)));
    console.log("full payload:", payload);
    console.groupEnd();
  }

  _logResponse(data) {
    const next = data.next_field_key;
    console.group(`[QIQ:${this.instanceId.slice(0, 8)}] <- /evaluate response`);
    console.log("next_field_key:", next ?? "(none - final result)");
    if (next) {
      console.log("field:", data.field);
    } else {
      console.log("status:",       data.result?.meta?.status);
      console.log("edr_id:",       data.edr_id);
      console.log("pdf_url:",      data.pdf_url);
      console.log("export_error:", data.export_error ?? null);
    }
    console.log("raw:", data);
    console.groupEnd();
  }

  // ── Element refs ──────────────────────────────────────────────

  _bindElements() {
    const r   = this.root;
    const ref = name => r.querySelector(`[data-qiq-ref="${name}"]`);

    this.els = {
      progress:      r.querySelector(".qiq-progress-bar"),

      // Layer 1
      layer1:        r.querySelector(".qiq-layer-1"),
      nameInput:     ref("name"),
      emailInput:    ref("email"),
      nameField:     ref("name-field"),
      emailField:    ref("email-field"),
      submitBtn:     ref("submit"),

      // Layer 2
      layer2:        r.querySelector(".qiq-layer-2"),
      messages:      r.querySelector(".qiq-chat-messages"),
      chatInput:     ref("chat-input"),
      sendBtn:       ref("send-btn"),

      // Layer 3
      layer3:        r.querySelector(".qiq-layer-3"),
      resultContent: r.querySelector(".qiq-result-content"),
      pdfBtn:        ref("pdf-btn"),
      callBtn:       ref("call-btn"),
      callLink:      ref("call-link"),
    };

    this.els.submitBtn.addEventListener("click", () => this._handleEmailSubmit());
    this.els.nameInput.addEventListener("keydown",  e => { if (e.key === "Enter") this.els.emailInput.focus(); });
    this.els.emailInput.addEventListener("keydown", e => { if (e.key === "Enter") this._handleEmailSubmit(); });

    this.els.sendBtn.addEventListener("click", () => this._handleChatSend());
    this.els.chatInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this._handleChatSend(); }
    });
  }

  // ── Dotted key helper ─────────────────────────────────────────

  // Sets obj["routing"]["work_relationship"] from key "routing.work_relationship"
  _setDotted(obj, dottedKey, value) {
    const parts = dottedKey.split(".");
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof cur[parts[i]] !== "object" || cur[parts[i]] === null) {
        cur[parts[i]] = {};
      }
      cur = cur[parts[i]];
    }
    cur[parts[parts.length - 1]] = value;
  }

  // ── Layer navigation ──────────────────────────────────────────

  _showLayer(n) {
    const prev = this.currentLayer;
    this.currentLayer = n;
    [this.els.layer1, this.els.layer2, this.els.layer3].forEach((el, i) => {
      el.classList.toggle("active", i + 1 === n);
    });
    const pct = { 1: "10%", 2: "55%", 3: "100%" }[n];
    if (this.els.progress) this.els.progress.style.width = pct;
    this._log(`layer transition ${prev} -> ${n}`, { progress: pct });
  }

  // ── Layer 1: Email Capture ────────────────────────────────────

  _handleEmailSubmit() {
    const name  = this.els.nameInput.value.trim();
    const email = this.els.emailInput.value.trim();
    let valid = true;

    this._clearFieldError(this.els.nameField);
    this._clearFieldError(this.els.emailField);

    if (!name) {
      this._setFieldError(this.els.nameField, "Please enter your name.");
      valid = false;
    }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      this._setFieldError(this.els.emailField, "Please enter a valid email address.");
      valid = false;
    }
    if (!valid) return;

    this.session.name  = name;
    this.session.email = email;

    this._log("email captured", { name, email });
    this._showLayer(2);
    this._startChat();
  }

  _setFieldError(fieldEl, msg) {
    fieldEl.classList.add("has-error");
    fieldEl.querySelector(".field-error").textContent = msg;
  }

  _clearFieldError(fieldEl) {
    fieldEl.classList.remove("has-error");
  }

  // ── Layer 2: Chat Dialog ──────────────────────────────────────

  _startChat() {
    this._addBotMessage(
      `Hi ${this.session.name}! I'll ask you a few quick questions to check your eligibility. Let's get started.`
    );
    this._callEvaluate();
  }

  _handleChatSend() {
    if (this.isWaiting) return;
    const text = this.els.chatInput.value.trim();
    if (!text) return;

    this.els.chatInput.value = "";
    this._submitAnswer(text);
  }

  // Called by both text input and choice button clicks
  _submitAnswer(value) {
    this._addUserMessage(value);
    if (this._pendingFieldKey) {
      this._setDotted(this.answers, this._pendingFieldKey, value);
      this._log("answer stored", {
        field: this._pendingFieldKey,
        value,
        answers: JSON.parse(JSON.stringify(this.answers)),
      });
    }
    this._callEvaluate();
  }

  async _callEvaluate() {
    this.isWaiting = true;
    this.els.sendBtn.disabled = true;
    this.els.chatInput.disabled = true;

    const typingEl = this._addTypingIndicator();

    // Spread nested answers as top-level keys alongside identity fields.
    // The backend's _get_dotted() traverses e.g. payload.routing.work_relationship.
    const payload = {
      ...JSON.parse(JSON.stringify(this.answers)),
      session_id: this.instanceId,
      full_name:  this.session.name,
      email:      this.session.email,
      ...(this.opts.pathway && { pathway: this.opts.pathway }),
    };

    this._logRequest(payload);

    console.log('[QIQ DEBUG] this.opts.apiBase:', this.opts.apiBase);
    console.log('[QIQ DEBUG] Calling fetch with URL:', `${this.opts.apiBase}/evaluate`);

    try {
      const res = await fetch(`${this.opts.apiBase}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
      const data = await res.json();

      this._logResponse(data);
      this._handleEvaluateResponse(data);

    } catch (err) {
      this._log("evaluate error", { message: err.message, stack: err.stack });
      this._addBotMessage("Sorry, something went wrong. Please try again.");
      this._setInputMode("text");
    } finally {
      typingEl.remove();
      this.isWaiting = false;
      this.els.sendBtn.disabled = false;
      this.els.chatInput.disabled = false;
      if (this._pendingInputType === "text" || this._pendingInputType === "number") {
        this.els.chatInput.focus();
      }
    }
  }

  _handleEvaluateResponse(data) {
    const nextKey = data.next_field_key;

    if (nextKey) {
      this._pendingFieldKey = nextKey;
      const field    = data.field || {};
      const question = field.label || field.prompt || nextKey;
      const itype    = field.input_type || "text";
      const choices  = field.choices    || [];

      this._pendingInputType = itype;
      this._addBotMessage(question, itype, choices);
      this._setInputMode(itype);
    } else {
      this._showResults(data);
    }
  }

  // Show or hide the text input row based on field type
  _setInputMode(itype) {
    const isTextInput = itype === "text" || itype === "number";
    this.els.chatInput.style.display  = isTextInput ? "" : "none";
    this.els.sendBtn.style.display    = isTextInput ? "" : "none";
    if (itype === "number") {
      this.els.chatInput.setAttribute("type", "number");
      this.els.chatInput.placeholder = "Enter a number...";
    } else {
      this.els.chatInput.setAttribute("type", "text");
      this.els.chatInput.placeholder = "Type your answer…";
    }
  }

  // ── Message helpers ───────────────────────────────────────────

  _addBotMessage(text, itype = "text", choices = []) {
    const msg = document.createElement("div");
    msg.className = "qiq-msg bot";

    let choiceHtml = "";

    if ((itype === "choice" || itype === "multi_choice") && choices.length) {
      const isMulti = itype === "multi_choice";
      const btnClass = isMulti ? "qiq-choice-btn qiq-choice-multi" : "qiq-choice-btn";
      choiceHtml = `
        <div class="qiq-choices" data-multi="${isMulti}">
          ${choices.map(c => `<button class="${btnClass}" data-value="${this._escapeHtml(c)}">${this._escapeHtml(_qiqDisplayChoiceLabel(c))}</button>`).join("")}
          ${isMulti ? `<button class="qiq-choice-confirm" style="display:none">Confirm selection</button>` : ""}
        </div>`;
    }

    msg.innerHTML = `
      <div class="qiq-msg-content">
        <div class="qiq-msg-bubble">${this._escapeHtml(text)}</div>
        ${choiceHtml}
      </div>`;

    this._wireChoiceButtons(msg, itype === "multi_choice");
    this.els.messages.appendChild(msg);
    this._scrollToBottom();
    return msg;
  }

  _wireChoiceButtons(msgEl, isMulti) {
    const btns    = msgEl.querySelectorAll(".qiq-choice-btn");
    const confirm = msgEl.querySelector(".qiq-choice-confirm");
    if (!btns.length) return;

    if (!isMulti) {
      btns.forEach(btn => {
        btn.addEventListener("click", () => {
          if (this.isWaiting) return;
          btns.forEach(b => { b.disabled = true; b.classList.remove("selected"); });
          btn.classList.add("selected");
          this._submitAnswer(btn.dataset.value);
        });
      });
    } else {
      // Multi-choice: toggle selection, show confirm when at least one selected
      btns.forEach(btn => {
        btn.addEventListener("click", () => {
          if (this.isWaiting) return;
          btn.classList.toggle("selected");
          const anySelected = [...btns].some(b => b.classList.contains("selected"));
          if (confirm) confirm.style.display = anySelected ? "" : "none";
        });
      });

      if (confirm) {
        confirm.addEventListener("click", () => {
          if (this.isWaiting) return;
          const selected = [...btns]
            .filter(b => b.classList.contains("selected"))
            .map(b => b.dataset.value);
          if (!selected.length) return;
          btns.forEach(b => b.disabled = true);
          confirm.disabled = true;
          this._submitAnswer(selected.join(", "));
        });
      }
    }
  }

  _addUserMessage(text) {
    const msg = document.createElement("div");
    msg.className = "qiq-msg user";
    msg.innerHTML = `<div class="qiq-msg-bubble">${this._escapeHtml(text)}</div>`;
    this.els.messages.appendChild(msg);
    this._scrollToBottom();
    return msg;
  }

  _addTypingIndicator() {
    const msg = document.createElement("div");
    msg.className = "qiq-msg bot qiq-typing";
    msg.innerHTML = `
      <div class="qiq-msg-avatar">Q</div>
      <div class="qiq-msg-content">
        <div class="qiq-msg-bubble">
          <div class="qiq-typing-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>`;
    this.els.messages.appendChild(msg);
    this._scrollToBottom();
    return msg;
  }

  _scrollToBottom() {
    const el = this.els.messages;
    el.scrollTop = el.scrollHeight;
  }

  // ── Layer 3: Results ──────────────────────────────────────────

  _showResults(data) {
    this._showLayer(3);

    const result  = data.result || {};
    const meta    = result.meta || {};
    const status  = meta.status    || "needs_review";
    const clars   = result.clarifications || [];
    const pdfUrl  = data.pdf_url ? `${this.opts.apiBase}${data.pdf_url}` : null;

    this._log("showing results", { status, pdfUrl, edrId: data.edr_id, clarCount: clars.length });

    // Default summary per status when backend returns empty string
    const DEFAULT_SUMMARY = {
      eligible:     "You meet the eligibility requirements for this visa category.",
      not_eligible: "You do not currently meet all mandatory requirements.",
      needs_review: "Eligibility cannot be confirmed yet due to pending verification.",
    };
    const summary = result.summary || DEFAULT_SUMMARY[status] || "";

    // ── Build injected content ──────────────────────────────────
    let html = "";

    // Eligibility Summary block
    html += `<div class="qiq-summary-block">`;
    html += `<h3>Eligibility Summary</h3>`;
    html += `<div class="qiq-summary-meta">`;
    html += `<span>Status: ${this._escapeHtml(status)}</span>`;
    if (meta.work_type) html += `<span>Work Type: ${this._escapeHtml(meta.work_type)}</span>`;
    if (meta.visa_type) html += `<span>Visa Type: ${this._escapeHtml(meta.visa_type)}</span>`;
    html += `</div>`;
    if (summary) html += `<p class="qiq-summary-sentence">${this._escapeHtml(summary)}</p>`;
    html += `</div>`;

    // Clarifications
    if (clars.length) {
      html += `<h4 class="qiq-clars-heading">Clarifications</h4>`;
      html += `<div class="qiq-clars-list">`;
      clars.forEach(c => { html += this._renderClarification(c); });
      html += `</div>`;
    }

    this.els.resultContent.innerHTML = html;

    // ── Footer wiring ───────────────────────────────────────────
    if (pdfUrl) {
      this.els.pdfBtn.href = pdfUrl;
      this.els.pdfBtn.style.display = "inline-block";
    } else {
      this.els.pdfBtn.style.display = "none";
    }
    this.els.callBtn.href = this.opts.calendlyUrl;

    // Company name in "Book a consultation with ___"
    const companyNameEl = this.root.querySelector(".qiq-company-name");
    const rawName = this.opts.companyName || this.root.dataset.companyName || "";
    if (companyNameEl && rawName) companyNameEl.textContent = rawName;

    if (this.els.callLink) this.els.callLink.href = this.opts.calendlyUrl;
  }

  // ── Clarification card renderer ────────────────────────────────

  _renderClarification(c) {
    const e   = s => this._escapeHtml(s);
    let html  = `<div class="qiq-clar-card">`;

    html += `<h4 class="qiq-clar-title">${e(c.title || c.requirement || "")}</h4>`;
    if (c.clarification) {
      html += `<p class="qiq-clar-body">${e(c.clarification)}</p>`;
    }

    // Police clearance criteria
    if (c.police_clearance_requirement?.criteria?.length) {
      html += `<p class="qiq-sub-label">Police clearance requirements:</p>`;
      html += this._bulletList(c.police_clearance_requirement.criteria);
    }

    // Handling key-values ("no_criminal_record", "criminal_record_disclosed")
    if (c.handling && Object.keys(c.handling).length) {
      html += `<p class="qiq-sub-label">How this is handled:</p>`;
      for (const [k, v] of Object.entries(c.handling)) {
        html += `<p class="qiq-kv"><strong>${e(this._handlingLabel(k))}:</strong> ${e(v)}</p>`;
      }
    }

    // Boundary key-values — some render plain, some with a bold label
    if (c.boundary && Object.keys(c.boundary).length) {
      html += `<p class="qiq-sub-label">Important boundary:</p>`;
      for (const [k, v] of Object.entries(c.boundary)) {
        const label = this._boundaryLabel(k);
        if (label) {
          html += `<p class="qiq-kv"><strong>${e(label)}:</strong> ${e(v)}</p>`;
        } else {
          html += `<p class="qiq-sub-para">${e(v)}</p>`;
        }
      }
    }

    // Secondary evidence items
    if (c.secondary_evidence?.length) {
      html += `<p class="qiq-sub-label">Alternative Evidence Options:</p>`;
      html += `<div class="qiq-evidence-block">`;
      c.secondary_evidence.forEach(ev => { html += this._renderEvidenceItem(ev); });
      html += `</div>`;
    }

    html += `</div>`;
    return html;
  }

  _renderEvidenceItem(ev) {
    const e = s => this._escapeHtml(s);
    let html = `<div class="qiq-ev-item">`;
    html += `<p class="qiq-ev-label">${e(ev.label || ev.type || "")}</p>`;
    if (ev.description) html += `<p class="qiq-ev-desc">${e(ev.description)}</p>`;

    const SUB_KEYS = [
      ["should_state",      "Should state"],
      ["must_clearly_show", "Must clearly show"],
      ["must_include",      "Must include"],
      ["requirements",      "Requirements"],
      ["notes",             "Notes"],
    ];
    for (const [key, label] of SUB_KEYS) {
      if (ev[key]?.length) {
        html += `<p class="qiq-ev-sublabel">${label}:</p>`;
        html += this._bulletList(ev[key]);
      }
    }

    html += `</div>`;
    return html;
  }

  _bulletList(items) {
    const e = s => this._escapeHtml(s);
    return `<ul class="qiq-clar-list">${items.map(i => `<li>${e(i)}</li>`).join("")}</ul>`;
  }

  // Convert handling keys to readable labels
  _handlingLabel(key) {
    const MAP = {
      no_criminal_record:        "No record",
      criminal_record_disclosed: "Record disclosed",
      minimum_requirement:       "Minimum requirement",
    };
    return MAP[key] || key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  // Boundary keys: null = render as plain paragraph, string = bold label
  _boundaryLabel(key) {
    const PLAIN = new Set(["case_by_case_review", "case_by_case"]);
    if (PLAIN.has(key)) return null;
    const MAP = {
      legal_deferral:      "Legal guidance",
      minimum_requirement: "Minimum requirement",
    };
    return MAP[key] || key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  // ── Utils ─────────────────────────────────────────────────────

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
}

// Auto-init elements marked data-qiq-widget (only when loaded directly, not via embed.js)
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-qiq-widget]").forEach(el => {
    new QIQWidget(el, {
      apiBase:     el.dataset.apiBase     || "",
      calendlyUrl: el.dataset.calendlyUrl || "#",
      pathway:     el.dataset.pathway     || null,
      companyName: el.dataset.companyName || "",
    });
  });
});

// Expose to global scope for embed.js
window.QIQWidget = QIQWidget;
