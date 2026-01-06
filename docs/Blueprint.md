# QIQ — Blueprint (Build 2)

## 0. Purpose

This Blueprint defines **exactly what QualifyIQ is** for Build 2, with hard scope locks to prevent drift.

Build 2 is a **deterministic eligibility engine** with **dynamic questioning** for **three work relationships**.

---

## 1. What QIQ Is (Build 2 Definition)

QualifyIQ (Build 2) is an **eligibility decision engine** for **Costa Rica’s Digital Nomad visa**, delivered through a **chat-based web interface**.

It:

1. Presents a conversational chat UI embedded on the website.
2. Captures user inputs via that chat interface.
3. Routes questions dynamically based on **routing.work_relationship**.
4. Evaluates eligibility using **engine-executed rules** sourced from **locked policy artifacts**.
5. Returns a deterministic eligibility result and the deterministic next question.

---

## 2. Hard Scope Locks (Non-Negotiable)

### 2.1 Country + Visa Scope

* **Costa Rica only**
* **Digital Nomad visa only**

### 2.2 Work Relationships (Dynamic Routing)

Exactly three, mutually exclusive:

* **employee**
* **contractor**
* **business_owner**

#

---

## 3. Authority Model

### 3.1 Locked Policy Artifacts (Do Not Rewrite)

Eligibility logic is governed by overlay JSON loaded at runtime:

* `app/engine/overlays/overlay_employee.json`
* `app/engine/overlays/overlay_contractor.json`
* `app/engine/overlays/overlay_business_owner.json`

The engine evaluates rules defined by these overlays. The UI is non-authoritative.

### 3.2 Data Verification Policy

QIQ evaluates based on **self-reported information**.

The output must include a disclaimer:

> This evaluation is based on self-reported information. Official visa applications require verified documentation and government background checks.

---

## 4. Dynamic Questioning Contract (Authoritative)

This contract governs the interaction between the **chat UI** and the eligibility engine.

### 4.1 First Required Capture

The very first required field is:

* `routing.work_relationship`

This selection determines:

* which overlay loads
* which fields apply
* which rules are evaluated

### 4.2 Deterministic Next Field

The engine returns:

* `missing_fields` (deterministically ordered by **declared taxonomy order**)
* `next_field_key` (the first missing field by declared order)

### 4.3 Engine-Directed Questioning

The UI renders questions strictly as directed by the engine response.

The engine alone determines:

* completion
* required fields
* next_field_key

---

## 5. Eligibility Model (Only Decision Axis)

### 5.1 Eligibility Outcomes

The engine must return exactly one:

* **Eligible**
* **Ineligible**
* **Needs Review**

### 5.2 Meaning

* **Eligible:** All required gates satisfied per overlay.
* **Ineligible:** One or more hard gates failed per overlay.
* **Needs Review:** Ambiguity exists that cannot be resolved deterministically from user inputs (e.g., evidence uncertainty, practitioner-only interpretation), but no hard gate has conclusively failed.

---

## 6. Minimum Output Contract

The following response is consumed by the **chat UI** and any downstream systems.

The engine must produce an explainable response containing:

1. `eligibility_status` (Eligible | Ineligible | Needs Review)
2. `rule_results` (per rule: pass/fail/needs_review with reason)
3. `missing_fields` (ordered)
4. `next_field_key` (or null if complete)
5. `disclaimer_text`

No additional decision axes are permitted in Build 2.

---

## 7. System Boundaries (Authoritative)

QualifyIQ is responsible only for:

* capturing user inputs via the chat UI
* dynamically routing questions
* evaluating eligibility
* returning a structured result

QualifyIQ does **not**:

* store leads long-term
* run marketing or follow-up automations
* manage CRM pipelines

Downstream systems (e.g., CRM) may consume QIQ outputs but must not alter eligibility logic.

---

## 8. Session & Identity Rules

* Each interaction operates within a `session_id`.
* A session may be anonymous until an explicit identity field (e.g., email) is captured.
* **Certain identity fields (e.g., `identity.full_name`, `identity.email`) may be captured by upstream systems (e.g., Gravity Forms) and are considered external to the engine.**
* External identity fields are treated as missing **only if explicitly present and null**; absence does not imply missing.
* Session states are:

  * **in_progress** (missing_fields not empty)
  * **complete** (eligibility_status returned)
  * **abandoned** (session ends without completion)

The engine alone determines when a session is complete.

---

## 9. Rule Authority & Locking

Policy overlays are **source-of-truth artifacts**.

* Overlays must not be edited without a version bump.
* Code must treat overlays as immutable at runtime.
* Any change to eligibility logic requires an explicit overlay revision.

---

## 9.1 Authority Failure Behavior

If eligibility cannot be evaluated due to a missing, invalid, or incompatible policy artifact (including missing overlays, invalid rule references, or schema mismatches), the engine must **fail closed**.

In such cases, the engine returns:

* `eligibility_status = Needs Review`
* an explicit system-level reason indicating an authority failure

The engine must not infer, assume, or improvise eligibility outcomes when authoritative inputs are unavailable.

## 10. Determinism Requirement

QualifyIQ is strictly deterministic:

> Given the same inputs, the same declared taxonomy order, and the same overlay version, the engine must always return the same `eligibility_status`, `rule_results`, `missing_fields`, and `next_field_key`.

Determinism is defined by **taxonomy declaration order**, not by runtime discovery or first-seen ordering.

No probabilistic or heuristic decision-making is permitted.

---

## 11. Needs Review Constraint

`Needs Review` is permitted **only** when:

* a required determination cannot be computed because a required field is missing or ambiguous per overlay rules, and
* no hard eligibility gate has conclusively failed.

`Needs Review` must never be returned based on subjective judgment or inferred risk.

---

## 12. Rule Results Structure (Minimum)

Each entry in `rule_results` must contain:

* `rule_id`
* `status` (pass | fail | needs_review)
* `reason` (short, deterministic explanation)

Freeform or narrative-only rule outputs are not permitted.

---

## 13. Data Conventions

Unless otherwise specified:

* field names use `snake_case`
* dates use ISO-8601 format
* currency values include an explicit currency code

---

## 14. One-Sentence System Framing

> **“QualifyIQ dynamically routes questions through a chat interface and deterministically evaluates Costa Rica Digital Nomad eligibility.”**
