## Phase-0 Addendum v1.0

**Source:** Blueprint v1.4

---

## 1. Phase-0 Objective

Phase-0 exists to eliminate **regulatory ambiguity, numeric uncertainty, and rule drift** before engineering begins.

No new features are introduced.
No new domains are added.
This addendum strictly operationalizes Blueprint v1.4.

---

## 2. Phase-0 Requirements Classification (V1)

Phase-0 does **not** require inventing numbers.
It requires:

* locking what is explicitly stated by authoritative sources
* explicitly classifying what is *unspecified* or *practice-based*
* defining how those items affect **Eligibility** vs **Readiness**

### 2.1 Locked Government Requirements (Authoritative)

Locked from official guidance:

* **Minimum monthly income (USD):** $3,000 individual / $4,000 with dependents
* **Income must originate outside Costa Rica** (foreign-source income)
* **Valid passport required** (no minimum remaining validity explicitly stated)
* **Health insurance required for full stay**, including medical + isolation/quarantine-related accommodation (no numeric minimum explicitly stated)
* **Nationality:** no exclusions explicitly stated (treat as eligible-by-default)
* **Criminal background:** no DN-specific requirement explicitly stated (treat as informational only; general admissibility may apply)

### 2.2 Unspecified Items (Handled as Readiness / Soft Logic)

The following are **not** explicitly specified in authoritative guidance and must not be treated as hard gates:

* income proof duration (months)
* passport minimum remaining validity (months)
* insurance minimum coverage amount

Engine handling (V1):

* These items may produce **warnings, readiness penalties, or “conditional/needs-docs” outcomes**.
* They must **not** be used as sole reasons for “Unlikely Eligible.”

### 2.3 Practice-Based Inputs (Optional, Labeled)

If practitioner guidance is used (e.g., licensed immigration attorneys), it must be:

* labeled as **Practice-Based**
* assigned a confidence level
* used only for readiness scoring / advisory flags

---

## 3. Phase-0 Outputs (Deliverables)

Phase-0 is complete when the following exist:

1. **Phase-0 Constants Register (Spreadsheet)** with: value, source type, URL, authority, last verified date, confidence, lock status
2. **Eligibility vs Readiness classification** for all requirements (authoritative vs unspecified vs practice-based)
3. **Criminal background handling** explicitly set to: informational (not gating)
4. **Disclaimer text** finalized (minimum viable V1 wording acceptable)

All deliverables become inputs to Day 1 implementation.

---

## 4. Phase-0 Completion Rule

Phase-0 is complete when:

* All authoritative requirements are locked in the spreadsheet
* All ambiguous requirements are explicitly marked as **unspecified** and routed to readiness/flags (not hard gates)
* The disclaimer text is inserted and finalized

**Coding may begin once the above is true.**

---

## 5. Prototype Mode (Internal Only)

If you want to test that the system works end-to-end before DGME clarification:

* You may use **Prototype Assumptions** (temporary numbers) ONLY in a separate prototype constants file
* Prototype assumptions must be labeled **NON-AUTHORITATIVE** and must not be marked “Locked” in Phase-0
* Prototype assumptions must not be represented as official requirements

---

## 6. Phase-0 Scope Boundary

Phase-0 explicitly excludes:

* UX design
* API implementation
* CRM mapping
* Multi-country analysis
* Human oversight workflows

---

**Status:** Phase-0 Addendum v1.1 — aligned to Phase-0 Constants Register; ready to proceed
