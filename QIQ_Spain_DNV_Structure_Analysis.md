# QIQ Spain DNV Structure Analysis

Date: 2026-06-05

## Executive Summary

QIQ currently stores the working visa-question flow mostly as JSON taxonomy files under `app/engine/taxonomies/`, with deterministic navigation in Python (`app/engine/evaluator.py`) and deterministic eligibility in Python (`app/engine/eligibility_rules.py`). The frontend widget does not own pathway-specific question definitions; it asks the backend `/evaluate`, renders the returned `field`, and stores answers under the returned dotted `next_field_key`.

The current live backend is effectively a Costa Rica Digital Nomad Visa implementation, keyed first by `routing.work_relationship` (`contractor`, `employee`, or `business_owner`). The submitted `pathway` value (for example `costa-rica-dnv`) is passed through for widget/admin/lead metadata, but it does not select backend question files or eligibility rules.

No live `portugal_d7` pathway configuration was found. Portugal D7 appears only in `widget/mock_server.py` and widget flow tests as a mock/demo pathway. The Spain DNV Typeform workbook is now present at `data/source/Spain_DNV_Typeform_Questions.xlsx` and is analyzed in the Spain DNV Workbook Addendum below. The companion files `qiq_spain_dnv_project_setup.md` and `spain_dnv_qiq_scaffold.json` were still not present in the workspace.

## Exact Files Inspected

### Runtime Entry And Routing

- `main.py` — FastAPI `/evaluate` orchestration, navigation vs final evaluation, EDR/PDF/run persistence, lead notification.
- `widget/widget.js` — frontend chat widget, answer storage, question rendering, result rendering, Calendly/PDF behavior.
- `widget/embed.js` — embed loader, `data-pathway` extraction.
- `widget/index.html` — example widget markup with `data-pathway="costa-rica-dnv"`.
- `widget/test-embed.html` — widget embed test markup.
- `widget/test_flow.py` — widget integration flow test using `costa-rica-dnv`.
- `app/admin/static/admin.js` — admin pathway display parsing from saved `chat_log.input.pathway`.

### Question / Taxonomy Sources

- `app/engine/taxonomies/taxonomy_contractor.json` — contractor question/order taxonomy.
- `app/engine/taxonomies/taxonomy_employee.json` — employee question/order taxonomy.
- `app/engine/taxonomies/taxonomy_business_owner.json` — business-owner question/order taxonomy.
- `app/engine/evaluator.py` — loads the above taxonomy files and returns the next required field.
- `app/engine/evaluator_BU.py` — older/historical hard-coded evaluator backup, not imported by `main.py`.

### Eligibility / Rules Sources

- `app/engine/eligibility_rules.py` — active final eligibility calculation.
- `app/engine/evidence_validation.py` — income evidence sufficiency rules.
- `app/engine/overlays/overlay_contractor.json` — declarative rules overlay, apparently not used by active `/evaluate`.
- `app/engine/overlays/overlay_employee.json` — declarative rules overlay, apparently not used by active `/evaluate`.
- `app/engine/overlays/overlay_business_owner.json` — declarative rules overlay, apparently not used by active `/evaluate`.
- `tests/test_evaluate_determinism.py` — API contract and determinism tests.
- `tests/test_p14_regression_applicant_type.py` — applicant-type regression tests against `app.engine.evaluator.evaluate`.

### Output / CTA / Clarification Sources

- `app/engine/output_builder.py` — maps eligibility result to UI output, clarifications, and next steps.
- `app/engine/taxonomy_loader.py` — loads output and clarification taxonomies.
- `app/taxonomies/output/taxonomy_output_meta.json` — output metadata labels/statuses.
- `app/taxonomies/output/taxonomy_output_summary.json` — status summary statements.
- `app/taxonomies/output/taxonomy_output_cta.json` — next-step CTA variants.
- `app/taxonomies/clarification/taxonomy_clarification_background.json` — shared criminal-background clarification.
- `app/taxonomies/clarification/taxonomy_clarification_contractor.json` — contractor clarification blocks.
- `app/taxonomies/clarification/taxonomy_clarification_employee.json` — employee clarification blocks.
- `app/taxonomies/clarification/taxonomy_clarification_business_owner.json` — business-owner clarification blocks.
- `clarification/*.json` — older/duplicate clarification taxonomy files outside the active `app/taxonomies` loader path.
- `app/outputs/result_schema.py` — Pydantic result schema/status vocabulary.
- `app/outputs/evaluate_response.py` — wrapper response schema compatibility code, not used directly by `main.py` response construction.
- `app/core/eligibility_decision_record.py` — EDR schema and final decision record shape.

### Portugal D7 / Mock Sources

- `widget/mock_server.py` — mock `/evaluate` server with a simple Portugal D7 script and income threshold.
- `widget/test_flow.py` — uses mock-style answers including `target_country: Portugal` while still sending `pathway: costa-rica-dnv`.

### Spain DNV Source Files Requested By User

These exact files were searched for:

- `data/source/Spain_DNV_Typeform_Questions.xlsx` — found and inspected.
- `qiq_spain_dnv_project_setup.md` — not found.
- `spain_dnv_qiq_scaffold.json` — not found.

## File Formats Used

- JSON: active taxonomy/question files, clarification taxonomies, output CTA/summary/meta taxonomies, inactive overlays, persisted run/EDR exports.
- Python dict/list logic: active question navigation logic, active eligibility logic, output assembly, evidence validation, mock Portugal D7 script.
- HTML/JS/CSS: widget shell, frontend rendering, static marketing/admin/demo pages.
- No YAML files were found for pathway/question/rule configuration.
- No DB seed files were found for pathway/question/rule configuration. Runs and sessions are persisted as JSON files under `data/`.
- No Excel ingestion code was found.

## Current QIQ Data Structure

### Request Payload Shape

The widget sends a single JSON object to `POST /evaluate`. Answers are nested according to dotted field keys:

```json
{
  "session_id": "uuid-like-widget-instance-id",
  "full_name": "Applicant Name",
  "email": "applicant@example.com",
  "pathway": "costa-rica-dnv",
  "routing": {
    "work_relationship": "contractor",
    "applicant_type": "individual",
    "income_foreign_only": "yes"
  },
  "role": {
    "contractor": {
      "monthly_income_usd": "3500",
      "income_evidence_types": "bank_statements, invoices, contracts, tax_returns",
      "income_evidence_months": "12"
    }
  },
  "identity": {
    "nationality": "United States"
  }
}
```

Important storage buckets:

- `routing.*` — common routing and general eligibility answers.
- `role.contractor.*` — contractor income/evidence answers.
- `role.employee.*` — employee income/evidence answers.
- `role.business_owner.*` — business-owner income/evidence answers.
- `identity.*` — applicant identity attributes used in eligibility/intake, separate from top-level lead identity.
- Top-level `full_name`, `email`, `phone`, `session_id`, `pathway` — lead/session/admin metadata, not current eligibility rule inputs.

### Navigation Response Shape

When more information is needed, `main.py` returns a navigation response:

```json
{
  "result": {
    "missing_fields": ["routing.income_foreign_only"],
    "next_field_key": "routing.income_foreign_only",
    "field": {
      "label": "Is all of your income sourced from outside Costa Rica?",
      "input_type": "choice",
      "choices": ["yes", "no"]
    }
  },
  "next_field_key": "routing.income_foreign_only",
  "missing_fields": ["routing.income_foreign_only"],
  "field": {
    "label": "Is all of your income sourced from outside Costa Rica?",
    "input_type": "choice",
    "choices": ["yes", "no"]
  },
  "edr_id": null,
  "pdf_url": null
}
```

The frontend primarily uses top-level `next_field_key` and top-level `field`.

### Final Response Shape

When intake is complete, `main.py` evaluates eligibility, builds output, persists EDR/run records, optionally creates PDF, and returns:

```json
{
  "result": {
    "meta": {
      "status": "eligible",
      "work_type": "contractor",
      "visa_type": "Digital Nomad"
    },
    "summary": "Based on the information provided, you meet the eligibility requirements.",
    "clarifications": [],
    "next_steps": {
      "enabled": true,
      "text": ["If you would like assistance preparing or reviewing your application, professional support is available."],
      "action": {
        "label": "Book a consultation with Great Expatations",
        "type": "link"
      }
    }
  },
  "next_field_key": null,
  "missing_fields": [],
  "field": null,
  "edr_id": "...",
  "edr_url": "/exports/edr_....json",
  "pdf_url": "/reports/edr_....pdf",
  "run_id": "...",
  "export_error": null
}
```

## How A Pathway Is Registered Or Discovered

There is no active backend pathway registry keyed by `portugal_d7`, `costa-rica-dnv`, or `spain_dnv`.

Current discovery works like this:

1. The widget reads `data-pathway` from HTML via `widget/embed.js` and/or widget initialization.
2. The widget includes `pathway` as top-level metadata in `/evaluate` requests.
3. `main.py` passes `pathway` only to lead notification and saved run/chat log metadata.
4. The actual question set is selected by `routing.work_relationship`, not `pathway`.
5. `app/engine/evaluator.py` loads `app/engine/taxonomies/taxonomy_{work_relationship}.json` after `routing.work_relationship` is answered.
6. `app/admin/static/admin.js` parses `pathway` only for display, converting slugs like `costa-rica-dnv` to country/visa labels.

Implication for Spain DNV: adding `data-pathway="spain-dnv"` or `spain_dnv` alone will not change backend questions, rules, or output. Spain-specific behavior requires either modifying the existing engine logic or adding a real pathway registry/dispatcher.

## Required Question Fields

### Active Taxonomy Question Object

The active taxonomy files use objects in `taxonomy_fields` with these fields:

| Field | Required By Loader | Used By Runtime | Notes |
|---|---:|---:|---|
| `key` | Yes | Yes | Dotted storage key and effective question ID. Must be a string. |
| `depends_on` | No | Loaded but mostly informational | Preserves dependency metadata; active evaluator does not enforce generic dependency ordering beyond field order and hard-coded family skip. |
| `label` | No | Yes | Prompt text displayed by widget. If missing, widget falls back to `field.prompt`, then `next_field_key`. |
| `input_type` | No | Yes | Widget supports `text`, `number`, `choice`, `multi_choice`; hyphens normalized to underscores. Defaults to `text`. |
| `choices` | No | Yes for choice types | Array of raw answer values; frontend also displays prettified labels. |
| `applies_when` | No | Partially/mostly not active | Loaded, but active `_applies_when_true()` always returns `True`. Family dependent fields are skipped via hard-coded key checks. |

### Fields Asked In The User Request

- Question ID: use `key`; there is no separate `id` field in active taxonomy.
- Prompt text: use `label`; mock server also supports `prompt`, and widget falls back to `prompt`, but active taxonomy uses `label`.
- Answer type: use `input_type`.
- Answer choices: use `choices` array for `choice` or `multi_choice`.
- Required/optional status: no explicit `required` field. All taxonomy fields are required if reached and not skipped.
- Storage key: same as `key`; dotted path controls nested payload storage.
- Conditional display logic: currently `applies_when` exists in JSON, but only family/dependent logic is actually enforced by Python key-name checks. Generic `applies_when` is not implemented.

## Field-By-Field Formatting Rules

### Question Formatting Rules

- File location: `app/engine/taxonomies/taxonomy_{work_relationship}.json` for current engine.
- Top-level object requires `work_relationship` and `taxonomy_fields`.
- `taxonomy_fields` order is question order after the two hard gates.
- `key` must be a dotted path that the backend can traverse, such as `routing.passport_validity_months` or `role.contractor.monthly_income_usd`.
- Dotted-key first segment should be one of the initialized buckets: `routing`, `identity`, `role`, or `income`. The widget can create other buckets, but `evaluator.py` only ensures those four exist.
- `input_type` should be one of `text`, `number`, `choice`, `multi_choice`.
- Choice values should be stable machine values, lowercase snake_case or numeric strings.
- For `number`, frontend stores the input as a string; backend casts as needed.
- For `multi_choice`, frontend currently stores selected values as a single comma-separated string, not an array.
- `depends_on` should be an array of dotted keys, even though current runtime does not generically enforce it.
- `applies_when` currently appears as `{ "equals": ["routing.applicant_type", "family"] }`; generic support must be implemented before relying on it beyond dependent-family fields.

### Answer Value Formatting Rules

- `choice`: raw string equal to the selected `choices[]` value.
- `multi_choice`: raw strings joined as `", "` by widget, e.g. `"bank_statements, invoices"`.
- `number`: frontend sends a string from an `<input type="number">`; backend converts with `float()` or `int()`.
- `text`: raw user-entered string.
- Boolean-like questions should use string values (`"yes"`, `"no"`, `"have_it"`, `"will_obtain"`), because active eligibility rules compare strings.
- Avoid boolean `true`/`false` in active taxonomy choices unless eligibility logic is updated; inactive overlays currently contain boolean `pass` values that do not match active string choices.

### Status Formatting Rules

Active status vocabulary is:

- `eligible`
- `needs_review`
- `not_eligible`

Important mismatch: `taxonomy_output_cta.json` and `taxonomy_output_meta.json` contain `ineligible`, while active Python returns `not_eligible`. `output_builder.py` has a fallback for `not_eligible` next steps, but taxonomy-driven CTA/meta variants for `ineligible` will not match `not_eligible` unless normalized.

## Example Question Object In Correct Current QIQ Format

```json
{
  "key": "routing.spain_residency_status",
  "depends_on": ["routing.work_relationship"],
  "label": "Are you currently legally residing in Spain or applying from outside Spain?",
  "input_type": "choice",
  "choices": ["in_spain_legal", "outside_spain", "in_spain_irregular"]
}
```

Note: this object is structurally valid for the current taxonomy loader. It is not sufficient by itself for Spain-specific branching or eligibility unless the evaluator/rules are extended to load Spain-specific taxonomies and evaluate Spain-specific requirements.

## Branching / Jump Logic

Current live branching is minimal:

1. `routing.work_relationship` is always asked first if missing.
2. `routing.applicant_type` is always asked second if missing.
3. Then the evaluator loads `taxonomy_{work_relationship}.json`.
4. It iterates `taxonomy_fields` in array order and returns the first missing field.
5. Dependent fields are skipped if `routing.applicant_type != "family"` when the key is `routing.dependents_count` or starts with `routing.dependent`.
6. Generic `applies_when` is loaded but not actually evaluated; `_applies_when_true()` always returns `True`.
7. There is no Typeform-style `jump` object, `go_to`, `next`, rule graph, or per-answer branch map in the active backend.
8. There is no frontend jump logic; frontend waits for backend `next_field_key`.

## Example Logic Rule In Correct Current QIQ Format

### Actually Active Conditional Logic

The only reliable current conditional question logic is encoded by question key naming and Python logic. The JSON marker looks like this:

```json
{
  "key": "routing.dependents_count",
  "depends_on": ["routing.applicant_type"],
  "label": "How many dependents are included in your application?",
  "input_type": "number",
  "applies_when": {
    "equals": ["routing.applicant_type", "family"]
  }
}
```

Runtime behavior: this works only because `evaluator.py` hard-codes skipping dependent keys unless `routing.applicant_type == "family"`, not because it evaluates `applies_when` generically.

### Inactive Overlay Rule Shape

There are declarative JSON rule overlays under `app/engine/overlays/`, but `main.py` does not call an overlay evaluator. Their shape is:

```json
{
  "rule_id": "DN_MIN_MONTHLY_INCOME",
  "field_keys": [
    "role.contractor.monthly_income_usd",
    "routing.applicant_type"
  ],
  "test": "gte_threshold_by_applicant_type",
  "pass": {
    "individual": 3000,
    "family": 4000
  },
  "fail_outcome": "ineligible",
  "user_facing_meaning": "Monthly income must meet the minimum for your applicant type.",
  "inline_support": "Enter gross monthly average in USD."
}
```

Do not rely on this format for implementation unless the overlay evaluator is restored or added.

## Eligibility Calculation

Active eligibility is calculated in `app/engine/eligibility_rules.py` after `evaluate()` returns `next_field_key: null`.

### Current Rules

- Minimum monthly income: `INCOME_MIN_MONTHLY_USD = 3000`.
- Minimum income evidence duration: `INCOME_MIN_MONTHS = 12`.
- Minimum passport validity: `PASSPORT_MIN_MONTHS = 6`.
- Work type selects income paths:
  - `role.contractor.monthly_income_usd`
  - `role.employee.monthly_income_usd`
  - `role.business_owner.monthly_income_usd`
- Work type selects income duration paths:
  - `role.contractor.income_evidence_months`
  - `role.employee.income_evidence_months`
  - `role.business_owner.income_evidence_months`
- Work type selects evidence paths:
  - `role.contractor.income_evidence_types`
  - `role.employee.income_evidence_types`
  - `role.business_owner.income_evidence_types`
- `validate_income_evidence()` checks selected evidence against hard-coded required sets.
- `routing.income_foreign_only` must equal `"yes"`.
- `routing.passport_validity_months` must be at least `6`.
- `routing.background_check_available` and `routing.criminal_record_flag` are treated as review/informational signals but currently do not append failures in active logic.

### Current Outcome Resolution

- If any hard failure exists, status is `not_eligible`.
- Else if any non-hard failed requirement exists, status is `needs_review`.
- Else status is `eligible`.

Hard failures:

- `income_amount`
- `income_duration_months`
- `foreign_income`
- `passport_validity`

Soft/review failures usually come from missing evidence keys returned by `validate_income_evidence()`.

## Example Eligibility Outcome In Correct Current QIQ Format

Active `evaluate_eligibility()` returns this internal shape:

```json
{
  "eligibility_status": "not_eligible",
  "failed_requirements": [
    "income_amount",
    "income_duration_months"
  ],
  "routing": {
    "work_relationship": "contractor",
    "applicant_type": "individual",
    "income_foreign_only": "yes",
    "passport_validity_months": "12"
  },
  "work_type": "contractor",
  "visa_type": "Digital Nomad"
}
```

`build_output()` maps that to frontend output:

```json
{
  "meta": {
    "status": "not_eligible",
    "work_type": "contractor",
    "visa_type": "Digital Nomad"
  },
  "summary": "Based on the information provided, you do not meet the eligibility requirements.",
  "clarifications": [
    {
      "requirement": "income_duration_months",
      "title": "Income History Duration",
      "clarification": "Costa Rica's Digital Nomad visa requires proof of stable business income for at least 12 consecutive months. This is a mandatory requirement with no exceptions."
    }
  ],
  "next_steps": {
    "enabled": true,
    "text": [
      "Unfortunately, you do not currently meet the mandatory requirements for Costa Rica's Digital Nomad visa.",
      "If your situation changes in the future, you may reapply once all requirements are satisfied."
    ]
  }
}
```

## Taxonomy Field Structure

### Question Taxonomies

Current question taxonomies are split by work relationship:

- `app/engine/taxonomies/taxonomy_contractor.json`
- `app/engine/taxonomies/taxonomy_employee.json`
- `app/engine/taxonomies/taxonomy_business_owner.json`

Top-level shape:

```json
{
  "work_relationship": "contractor",
  "taxonomy_fields": [
    {
      "key": "routing.work_relationship",
      "depends_on": [],
      "label": "What best describes your work relationship?",
      "input_type": "choice",
      "choices": ["contractor", "employee", "business_owner"]
    }
  ]
}
```

### Clarification Taxonomies

Clarification taxonomies live under `app/taxonomies/clarification/`. The loader indexes each file by top-level `work_type` or `scope`.

Work-type shape:

```json
{
  "scope": "contractor",
  "clarifications": [
    {
      "requirement": "income_duration_months",
      "title": "Income History Duration",
      "clarification": "...",
      "boundary": {
        "minimum_requirement": "...",
        "case_by_case": "..."
      }
    }
  ]
}
```

Shared/background shape:

```json
{
  "scope": "all_work_types",
  "requirement": "criminal_background",
  "title": "Criminal Background — Police Clearance",
  "clarification": "...",
  "police_clearance_requirement": {
    "required": true,
    "criteria": ["..."]
  }
}
```

### Output Taxonomies

Output taxonomies live under `app/taxonomies/output/`. The loader indexes each by top-level `section`.

Summary shape:

```json
{
  "section": "summary_statement",
  "driven_by": ["eligibility_status"],
  "variants": {
    "eligible": { "text": "...", "max_sentences": 1 },
    "needs_review": { "text": "...", "max_sentences": 1 },
    "ineligible": { "text": "...", "max_sentences": 1 }
  }
}
```

CTA shape:

```json
{
  "section": "next_steps_cta",
  "driven_by": ["eligibility_status"],
  "variants": {
    "eligible": {
      "enabled": true,
      "text": ["..."],
      "action": { "label": "Book a consultation with Great Expatations", "type": "link" }
    },
    "needs_review": {
      "enabled": true,
      "text": ["..."],
      "action": { "label": "Book a consultation with Great Expatations", "type": "link" }
    },
    "ineligible": {
      "enabled": true,
      "text": ["..."],
      "action": { "label": "Book a consultation with Great Expatations", "type": "link" }
    }
  }
}
```

Again, `ineligible` should be changed or aliased to `not_eligible` for consistency with active Python status values.

## Final Outcomes And CTA Mapping

### Eligible

- Internal status: `eligible`.
- Output summary variant: `taxonomy_output_summary.json` → `variants.eligible.text`.
- CTA variant: `taxonomy_output_cta.json` → `variants.eligible`.
- Widget behavior: hides summary sentence, hides PDF button, embeds Calendly inline calendar if `calendlyUrl` is configured.
- Lead email: receives status and pathway metadata.

### Not Eligible

- Internal status: `not_eligible`.
- Output summary: active taxonomy uses `ineligible`, so `not_eligible` currently produces an empty taxonomy summary unless frontend default or fallback text is used.
- CTA variant: active taxonomy uses `ineligible`; `output_builder.py` has a hard-coded fallback for `not_eligible` next steps.
- Widget behavior: shows summary, clarifications, PDF button if generated, no inline calendar.

### Manual Review

- Internal status: `needs_review`.
- Output summary variant: `taxonomy_output_summary.json` → `variants.needs_review.text`.
- CTA variant: `taxonomy_output_cta.json` → `variants.needs_review`.
- Widget behavior: shows attorney-review banner: “An attorney will review your case...”; shows clarifications and PDF if generated.
- There is no status named `manual_review`; QIQ equivalent is `needs_review`.

### Consultation CTA

- Taxonomy CTA action is `type: "link"` with a label, but no URL in the taxonomy.
- Widget currently uses `calendlyUrl` option/data attribute for eligible inline scheduling.
- For non-eligible statuses, widget hides the call button and shows PDF if available; taxonomy `next_steps.action` is not directly rendered as a clickable link in current widget output.

### Email CTA

- No user-facing email CTA taxonomy was found.
- Email is captured before intake and used for lead notification and run metadata.
- Internal lead notification is sent by `app/notifications/lead_email.py` after final evaluation.

## Frontend / Backend ID Matching Requirements

Yes: frontend and backend must agree exactly on field IDs/storage keys.

- Backend returns `next_field_key` as a dotted key, e.g. `role.contractor.monthly_income_usd`.
- Widget stores the answer at that exact dotted key with `_setDotted()`.
- Next request includes the nested answer payload.
- Backend `_get_dotted()` checks that same path to decide whether the field is missing and to evaluate rules.

If a Spain DNV question key is changed in the taxonomy but not updated in eligibility logic, the answer will be collected but ignored by the rules. If a rule expects a key that is never returned as `next_field_key`, final evaluation may classify the applicant incorrectly due to missing/`None` values.

## Portugal D7 Finding

No production `portugal_d7` implementation was found.

- No `portugal_d7` config file exists.
- No `pathway` dispatcher recognizes `portugal_d7`.
- `widget/mock_server.py` contains a four-question mock script using plain keys (`applicant_type`, `years_experience`, `target_country`, `monthly_income`) and a Portugal D7 summary.
- The mock script is separate from the active `main.py` backend and does not use active taxonomies, dotted keys, EDR, output taxonomies, or active eligibility rules.

## Comparison To Spain DNV Source Files

The Spain DNV Typeform workbook is now present and has been analyzed in the Spain DNV Workbook Addendum. The companion setup/scaffold files are still not present, so comparison is complete for the workbook and pending for those two files.

Expected mapping once files are available:

| Spain Source | Likely Use In QIQ | Notes |
|---|---|---|
| `Spain_DNV_Typeform_Questions.xlsx` | Source of prompt text, answer choices, Typeform branching, required/optional fields | Must be converted to QIQ JSON taxonomy and Python/declarative rule logic. |
| `qiq_spain_dnv_project_setup.md` | Product/legal implementation notes, CTA/copy, pathway scope | Use to define pathway registry behavior, statuses, CTAs, final text, missing legal assumptions. |
| `spain_dnv_qiq_scaffold.json` | Likely closest source for QIQ-native field/rule scaffolding | Need to compare key names, answer values, rule IDs, output mapping to current QIQ conventions. |

Structural mismatches likely to resolve:

- Typeform may have per-answer jump logic; current QIQ has linear first-missing-field navigation with minimal conditional skips.
- Typeform may have separate question IDs and storage variables; current QIQ uses one dotted `key` as both ID and storage path.
- Typeform may represent multi-select as arrays; current widget stores comma-separated strings.
- Spain DNV requirements likely need pathway-specific thresholds and statuses; current rules are hard-coded Costa Rica DNV values.
- Source files may include CTA/email actions; current widget does not render taxonomy CTA links for non-eligible statuses and has no user-facing email CTA.

## Required Spain DNV Files To Create

Minimum implementation options:

### Option A — Minimal Current-Architecture Patch

Create/modify:

- `app/engine/taxonomies/taxonomy_contractor.json` — add Spain-compatible contractor questions if reusing work-type taxonomy.
- `app/engine/taxonomies/taxonomy_employee.json` — add Spain-compatible employee questions if reusing work-type taxonomy.
- `app/engine/taxonomies/taxonomy_business_owner.json` — add Spain-compatible business-owner questions if supported.
- `app/engine/eligibility_rules.py` — branch by `pathway` and implement Spain DNV thresholds/rules.
- `app/engine/output_builder.py` — make visa/country-specific summaries and clarifications possible.
- `app/taxonomies/clarification/taxonomy_clarification_*.json` — add Spain-specific clarification entries or split by pathway.
- `app/taxonomies/output/*.json` — fix status keys to `not_eligible` and add Spain-specific CTA/copy if needed.

Downside: this blends Spain into Costa Rica work-type files and keeps no true pathway registry.

### Option B — Recommended Pathway Registry

Create:

- `app/engine/pathways/spain_dnv/questions.json` — Spain DNV question taxonomy.
- `app/engine/pathways/spain_dnv/rules.json` or `rules.py` — Spain DNV eligibility rules.
- `app/engine/pathways/spain_dnv/output.json` — Spain DNV output/CTA/visa metadata, if pathway-specific output is needed.
- `app/engine/pathways/spain_dnv/clarifications.json` — Spain DNV clarification blocks.
- `app/engine/pathway_registry.py` — maps `pathway` values (`spain-dnv`, `spain_dnv`) to question/rule/output modules.

Modify:

- `app/engine/evaluator.py` — load taxonomy by `pathway` first, then work-type if needed.
- `app/engine/eligibility_rules.py` — dispatch to pathway-specific evaluator.
- `app/engine/output_builder.py` — load pathway-specific output taxonomies.
- `main.py` — pass `pathway` into final eligibility/output layers explicitly.
- `widget/index.html` / embed usage — set `data-pathway="spain-dnv"` for Spain DNV.
- Tests — add Spain DNV navigation and deterministic eligibility tests.

This is cleaner and avoids contaminating existing Costa Rica DNV assumptions.

## Missing Information Needed Before Implementation

1. The three requested Spain source files are missing from the workspace.
2. Confirm the canonical pathway ID: `spain-dnv`, `spain_dnv`, or another slug.
3. Confirm whether Spain DNV should coexist with Costa Rica DNV in the same app instance.
4. Confirm whether Spain DNV supports employees, contractors/freelancers, business owners, or another applicant taxonomy.
5. Confirm exact Spain DNV financial thresholds, including individual vs family/dependent thresholds and currency.
6. Confirm whether answers should be stored in USD, EUR, or original user-entered currency.
7. Confirm required Spain DNV legal categories/statuses and whether `needs_review` is acceptable for manual review.
8. Confirm exact CTA behavior for each status: inline Calendly, consultation link, email CTA, PDF, or no CTA.
9. Confirm whether multi-select answers must become arrays; if yes, update `widget/widget.js` and `evidence_validation.py` expectations.
10. Confirm whether Typeform jump logic must be faithfully replicated; if yes, implement generic `applies_when` or a rule graph.
11. Confirm whether output taxonomy should be pathway-specific and whether firm name/CTA URLs should be data-driven.
12. Resolve `ineligible` vs `not_eligible` status mismatch before adding new output variants.

## Implementation Notes For Spain DNV

- Do not assume `pathway` currently changes logic; it does not.
- Treat dotted `key` names as API contracts between backend, widget, saved runs, EDR, and eligibility rules.
- Keep choice values stable and machine-readable; display labels are generated by the widget and should not be used as rule inputs.
- If Typeform contains branching, current `applies_when` must be implemented properly before conversion.
- If Spain DNV has country-specific output, avoid hard-coded Costa Rica strings in `eligibility_rules.py` and `output_builder.py`.
- Add deterministic tests before or alongside implementation because the current test suite is built around stable `/evaluate` behavior.

## Spain DNV Workbook Addendum

Source inspected: `data/source/Spain_DNV_Typeform_Questions.xlsx`.

The workbook contains four sheets:

- `Questions` — 24 rows including Typeform fields, subfields, required flags, choice counts, and inline choice labels.
- `Choices` — per-choice IDs, refs, labels, and question refs.
- `Logic` — Typeform jump/set actions and final thank-you/redirect routing.
- `Screens` — Typeform metadata, hidden fields, variables, welcome screen, and thank-you/CTA screens.

### Workbook Metadata

From `Screens`:

- Form ID: `o0x98iMZ`.
- Form title: `Spain DNV with HubSpot meeting scheduler`.
- Display URL: `https://jzuc7mjlbj9.typeform.com/Spain-DNV`.
- Hidden fields: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `gclid`, `utm_var`, `utm_refname`.
- Variables: `score`, `tag_country_of_residence_tag`, `tag_country_of_residence_tag_2`.
- Welcome title: `Get Your FREE Consultation Call – Digital Nomad Visa for Spain`.

### Workbook Question Inventory

| Order | Typeform Field ID | Ref | Type | Required | QIQ Mapping Recommendation | Notes |
|---:|---|---|---|---:|---|---|
| 1 | `ytNb2osEdtQx` | `37778eea-f643-452a-abb2-528f21be84c9` | `multiple_choice` | Yes | `routing.service_interest` | Multi-select: DNV, tax services, or both. Current QIQ multi-choice stores comma-separated strings. |
| 2 | `YTITWUUlVbiD` | `826daa18-4b8e-4cc8-84ff-d2096ada4e2f` | `multiple_choice` | Yes | `routing.work_relationship` | Map Typeform labels to `business_owner`, `contractor`, `employee`. |
| 3 | `M37JBaIxrTp1` | `16e2b8cc-0b0d-4b85-ad85-f7c45684a3e9` | `multiple_choice` | Yes | `role.contractor.service_agreements_available` | Applies only when occupation is contractor/self-employed/freelancer. |
| 4 | `tfQHxbajLKFq` | `a823c5c3-c84a-4c4b-958d-6d2bb094a9b0` | `short_text` | Yes | `role.profession_description` | Current QIQ role paths are work-type specific; either add common `role.profession_description` support or duplicate under each work type. |
| 5 | `TCDwywToK0cN` | `9a537249-bd36-45dc-adf4-ae421a22d729` | `number` | Yes | `routing.dependents_count` | Label is prefixed `HIDE`; no Typeform logic points to it in the inspected logic, so likely hidden/skipped. Current QIQ has no hidden default-field mechanism. |
| 6 | `HIcFd74CmOwP` | `2e04cc58-1cf6-4a56-ade0-f9ddc93f340d` | `multiple_choice` | Yes | `income.gross_monthly_income_band_eur` | Typeform uses income bands, not exact numeric amount. Current QIQ rules expect exact numeric USD amounts. |
| 7 | `eoiE6TpRepoo` | `ffadcffd-7e0a-4c32-99c0-b3ac397a6dfd` | `long_text` | No | `routing.additional_information` | Optional. Current QIQ has no optional-field handling; omit from required taxonomy or add `required: false` support. |
| 8 | `OmvImTJEQbbN` | `08a62a64-d41d-4ae8-bd00-46b42a82df55` | `contact_info` | Group | top-level lead fields | QIQ captures name/email before chat; phone is optional top-level metadata. |
| 8.1 | `xfnLjPAvhEXE` | `82b7ee8a-d1eb-42bc-97da-e45c56894bc2` | `short_text` | Yes | `identity.first_name` or top-level `full_name` | HubSpot redirect uses this ref as `firstname`. |
| 8.2 | `Jt7axWsFyxCZ` | `08c089af-c362-45b7-a918-779815252727` | `short_text` | Yes | `identity.last_name` or top-level `full_name` | HubSpot redirect uses this ref as `lastname`. |
| 8.3 | `hqNlVysGvLBS` | `8f8f436b-455e-447c-b8a8-654cd09b5eab` | `phone_number` | Yes | top-level `phone` | QIQ run store already supports `phone`. |
| 8.4 | `4i1CjdiWBeAV` | `69f8f66c-4fd7-4d32-865b-0ada00ab9088` | `email` | Yes | top-level `email` | QIQ already captures this before intake. |
| 9 | `oKITr3iNpygv` | `196ae4bf-0314-4b51-96c2-883c408f6985` | `short_text` | Yes | `identity.nationality` | Existing QIQ already has `identity.nationality`. |
| 10 | `5Moc3WxTKVAa` | `1b1e2628-2692-40b9-8c7c-2b2f86fcc3bd` | `short_text` | Yes | `identity.country_of_residence_hidden` | Label is prefixed `HIDE`; logic jumps from this to consent, but the user-facing dropdown appears to be question 11. |
| 11 | `GNOQqIm3xTWo` | `1e255397-576b-4d4b-a89c-b2d4de75fbe1` | `dropdown` | Yes | `identity.country_of_residence` | 198 country choices. Current QIQ widget has no dropdown/autocomplete; rendering 198 choice buttons is poor UX. |
| 12 | `dxR7r0n6HIOy` | `2eecfa38-29f3-4d2c-8723-8030927d66de` | `inline_group` | Group | consent group | DNV consent group with four subfields. Current QIQ has no inline-group support; flatten to questions if needed. |
| 12.1 | `9u1DhcDKJDfG` | `22432e55-d778-4572-a598-09426cb39283` | `multiple_choice` | Yes | `consent.terms_conditions` | Choice: `Yes`. |
| 12.2 | `iahJEDt4NmTZ` | `403cd64a-8a0c-455b-8cc1-198324c8b145` | `multiple_choice` | Yes | `consent.privacy_policy` | Choice: `Yes`. |
| 12.3 | `kkQ3VYJBn4qV` | `c3bf500c-a351-4076-b0aa-b12660c508e9` | `multiple_choice` | Yes | `consent.judicial_data_processing` | Choice: `Yes`. |
| 12.4 | `B4jLEOYaqrOO` | `0bc34dc6-9a08-4a3b-85dd-2f94e53ccf7c` | `multiple_choice` | Yes | `consent.marketing` | Choices: `Yes`, `No`. |
| 13 | `M1pEgtVptG4R` | `a2914b4f-6f26-4e8e-8ccb-f52f12b22d42` | `inline_group` | Group | alternate consent group | Tax/general review consent group. |
| 13.1 | `qYcLO4r4xwJG` | `ca075235-c90f-43dc-b55a-d94410857de5` | `multiple_choice` | Yes | `consent.terms_and_privacy_combined` | Choice: `Yes`. |
| 13.2 | `rhwDlcLn1UIv` | `9338e524-c1ed-4ef3-a238-0486259114f1` | `multiple_choice` | Yes | `consent.marketing` | Choices: `Yes`, `No`. |

### Spain DNV Choice Value Formatting

The workbook stores verbose Typeform choice labels and stable Typeform `Choice Ref` UUIDs. QIQ should not store the long labels as rule inputs. Recommended QIQ machine values:

```json
{
  "routing.service_interest": [
    "digital_nomad_visa",
    "tax_services"
  ],
  "routing.work_relationship": [
    "business_owner",
    "contractor",
    "employee"
  ],
  "role.contractor.service_agreements_available": [
    "can_secure_service_agreements",
    "cannot_secure_service_agreements"
  ],
  "income.gross_monthly_income_band_eur": [
    "below_2800",
    "eur_2800_5000",
    "eur_5000_10000",
    "above_10000"
  ],
  "consent.*": [
    "yes",
    "no"
  ]
}
```

If exact Typeform traceability matters, store Typeform refs separately as metadata, for example `source_ref` or `typeform_ref`, but keep rule-facing answer values short and stable.

### Typeform Logic Summary

The `Logic` sheet has 17 actions. Its behavior is not equivalent to QIQ's current linear first-missing-field evaluator.

Important Typeform jumps:

1. From service interest (`37778eea...`):
   - If service interest is not `Digital Nomad VISA`, jump to `Contact Info`.
   - Otherwise jump to occupation.
2. From occupation (`826daa18...`):
   - If occupation is `Contractor / Self-employed / Freelancer`, jump to the service-agreements question.
   - Otherwise jump to profession description.
3. From service-agreements (`16e2b8cc...`):
   - Always jump to profession description.
4. From profession description (`a823c5c3...`):
   - Always jump to gross monthly income.
5. From nationality (`196ae4bf...`):
   - Always jump to country of residence dropdown.
6. From country of residence dropdown (`1e255397...`):
   - Set one of two low-country variables for a long list of countries.
   - Always jump to the DNV consent group.
7. From consent group (`a2914b4f...`):
   - Route to one of multiple thank-you/CTA outcomes based on DNV selection, contractor contract answer, income band, and low-country variables.

### Country Risk Logic

The workbook sets Typeform variables `tag_country_of_residence_tag` and `tag_country_of_residence_tag_2` to `Low CR Country` for a long list of country-of-residence choices. These variables are later used to decide whether a user gets direct booking vs email/manual-review-style follow-up.

This has no current QIQ equivalent. Recommended implementation options:

- Add `routing.country_risk_tag` or `identity.country_of_residence_risk` computed in Python from `identity.country_of_residence`.
- Or add a declarative `country_groups.json` for Spain DNV and compute tags during eligibility.
- Do not duplicate a 198-choice dropdown as 198 widget buttons; add dropdown/autocomplete support or capture country as text and normalize server-side.

### Typeform Outcome / CTA Mapping

The `Screens` sheet defines these final outcomes:

| Ref | Type | Title | QIQ Status Mapping | CTA Behavior |
|---|---|---|---|---|
| `a0481f11-73ef-4fc5-a5bf-f80bfba96e74` | `url_redirect` | `Spain DNV Call Eligible` | `eligible` | Redirect to HubSpot DNV free consultation URL with email/first/last/UTM params. |
| `a494a6ad-7a58-449e-a67e-2bd5bdea555c` | `url_redirect` | `Spain SEV Call Eligible` | likely `needs_review` or separate pathway | Redirect to HubSpot SEV consultation URL; this is not Spain DNV and may be an alternate service pathway. |
| `eba8def4-bc3a-4151-bcfe-5cf4325e8d8d` | `thankyou_screen` | `You may be eligible for Spain DNV — check your inbox now` | `needs_review` or `manual_email_followup` variant | Email CTA/follow-up instead of immediate booking. |
| `d625cd9f-fe46-4095-af1a-ad2a4395402b` | `thankyou_screen` | `Thank you for your interest!` | `needs_review` or `not_eligible` depending on rule cause | Generic review/fallback message. |
| `default_tys` | `thankyou_screen` | Typeform default | Ignore | Not relevant to QIQ. |

The workbook does not clearly define a hard `not eligible` screen. Applicants with below-€2,800 income appear to fall through to the generic review/fallback thank-you screen unless other Typeform behavior exists outside the exported logic. QIQ should explicitly decide whether `below_2800` means `not_eligible` or `needs_review`.

### Spain DNV Logic Rules In QIQ Terms

A direct QIQ interpretation of the Typeform final DNV eligibility routing would look like this:

```json
{
  "rule_id": "SPAIN_DNV_INCOME_BAND_MINIMUM",
  "field_keys": ["income.gross_monthly_income_band_eur"],
  "test": "not_equals",
  "pass": "below_2800",
  "fail_outcome": "not_eligible",
  "user_facing_meaning": "Gross monthly income must be at least €2,800 for the DNV path."
}
```

But the active QIQ runtime cannot execute that JSON overlay today. The equivalent active implementation would need Python logic in `app/engine/eligibility_rules.py` or a new pathway-specific rules module.

A Typeform-style direct-booking rule would be:

```json
{
  "rule_id": "SPAIN_DNV_DIRECT_BOOKING_ELIGIBLE",
  "all": [
    { "field": "routing.service_interest", "contains": "digital_nomad_visa" },
    { "field": "income.gross_monthly_income_band_eur", "not_equals": "below_2800" },
    { "field": "role.contractor.service_agreements_available", "not_equals": "cannot_secure_service_agreements" },
    { "field": "identity.country_of_residence_risk", "not_equals": "low_cr_country" }
  ],
  "status": "eligible",
  "cta_variant": "hubspot_dnv_direct_booking"
}
```

Current QIQ would need generic condition evaluation to support this shape.

### Correct QIQ Question Object For Spain DNV

```json
{
  "key": "income.gross_monthly_income_band_eur",
  "depends_on": ["role.profession_description"],
  "label": "What is your GROSS Monthly Income (pre-tax)? Please provide an accurate amount.",
  "input_type": "choice",
  "choices": [
    "below_2800",
    "eur_2800_5000",
    "eur_5000_10000",
    "above_10000"
  ]
}
```

This is correct for QIQ's current widget, but Spain DNV eligibility must be updated to evaluate income bands rather than numeric USD income.

### Spain DNV Files Needed After Workbook Analysis

Recommended new files if adding a real pathway layer:

- `app/engine/pathways/spain_dnv/questions.json` — converted `Questions` sheet with QIQ machine keys and choices.
- `app/engine/pathways/spain_dnv/choice_map.json` — optional mapping from Typeform labels/refs to QIQ values for auditability.
- `app/engine/pathways/spain_dnv/country_groups.json` — low-country group used by Typeform variables.
- `app/engine/pathways/spain_dnv/rules.py` or `rules.json` — Spain DNV status and CTA routing rules.
- `app/engine/pathways/spain_dnv/output.json` — Spain-specific eligible/review/not-eligible summaries and CTA variants, including HubSpot URLs.

If keeping the current architecture, at minimum modify:

- `app/engine/evaluator.py` — recognize `pathway: spain-dnv` and load Spain questions instead of Costa Rica work-type taxonomies.
- `app/engine/eligibility_rules.py` — branch to Spain DNV rules when `pathway` is Spain DNV.
- `app/engine/output_builder.py` — support Spain-specific CTA variants and HubSpot/email outcomes.
- `widget/widget.js` — add `dropdown`, optional field, inline-group/consent, and preferably array-based multi-select support.

### New Missing Decisions From Workbook

- Whether `Tax Consultation / Beckham Law / Tax setup / Annual Tax Return` should be included in QIQ Spain DNV or routed out as a non-DNV flow.
- Whether `Spain SEV Call Eligible` should be implemented as a separate pathway/outcome or treated as manual review inside Spain DNV.
- Whether `below_2800` is `not_eligible` or generic `needs_review`.
- Whether low-country users are still `eligible` but routed to email follow-up, or should be `needs_review`.
- Whether hidden fields and UTM params must be preserved in QIQ run records and CTA URLs.
- Whether QIQ should collect contact info before the chat as it currently does, or reproduce Typeform's later contact-info group.
- Whether consent fields are legally required inside QIQ before redirect/email CTA.
- Whether country of residence should be dropdown/autocomplete, free text, or normalized server-side.
