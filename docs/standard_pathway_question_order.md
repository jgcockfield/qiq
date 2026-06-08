# Standard QIQ Pathway Question Order

## Purpose

Use this template for every new QIQ pathway before creating `questions.json`, `rules.py`, `output.json`, or `clarifications.json`.

Costa Rica DNV is the QIQ reference model for question style and eligibility structure. New pathways should follow its qualification-first pattern: ask the core facts that determine fit, then ask targeted supporting questions only when they affect eligibility, review status, or routing. Do not refactor Costa Rica DNV to match newer pathway files.

## 1. Stage 1 Intake Fields

Stage 1 identifies the country and pathway before the pathway-specific backend question flow begins.

| Order | Field Key | Purpose | Input Type | Required | Notes |
|---:|---|---|---|---|---|
| 1 | `routing.country` | Select destination country. | `choice` | Yes | Example choices: `spain`, `costa_rica`. Keep country values stable and lowercase. |
| 2 | `routing.pathway` | Select the visa or residency pathway. | `choice` | Yes | Choices should be filtered by `routing.country`, such as `costa_rica_dnv`, `costa_rica_pensionado`, or `spain_dnv`. |
| 3 | Identity capture | Capture contact info if required by the surface. | `text` | Surface-specific | Inline widget may collect contact details outside the backend flow; Typeform-style pathways may include contact fields later in `questions.json`. |

Do not duplicate country/pathway selector questions inside every pathway file unless the pathway is intended to run without the shared Stage 1 selector.

## 2. Backend Question Order

Pathway-specific `questions.json` files should follow the Costa Rica DNV qualification-first order after Stage 1.

| Standard Order | Eligibility Category | Reference Field Keys | Required by Default | Costa Rica DNV Model Notes |
|---:|---|---|---|---|
| 1 | Work / income type | `routing.work_relationship`, `routing.applicant_type`, `role.<pathway_or_work_type>.<income_type>` | Yes | Start by classifying the applicant and income category. |
| 2 | Foreign-source income | `routing.income_foreign_only`, `role.<pathway>.pension_foreign_source_confirmed` | Yes when required | Ask as a qualification fact, not as a document-readiness item. |
| 3 | Income amount | `role.<work_type>.monthly_income_usd`, `income.gross_monthly_income_<currency>`, `role.pensionado.monthly_pension_usd` | Yes when income is a core requirement | Prefer numeric values; use bands only when the source pathway intentionally screens by bands. |
| 4 | Income evidence | `role.<work_type>.income_evidence_types`, `income.income_evidence_types`, `role.<pathway>.pension_certificate_available` | Yes when evidence affects status | Costa Rica DNV asks evidence type before duration. |
| 5 | Income duration | `role.<work_type>.income_evidence_months`, `income.income_history_months`, `role.<pathway>.pension_duration_type` | Yes when continuity matters | Ask how long the applicant can prove the income after evidence type. |
| 6 | Dependents | `routing.applicant_type`, `routing.dependents_count`, `routing.dependent_relationships`, `routing.dependent_ages`, `documents.dependent_documents_available` | Conditional | Ask dependent details only when dependents are included. |
| 7 | Nationality / residence | `identity.nationality`, `identity.country_of_residence` | Yes when relevant | Costa Rica DNV asks nationality after core income/dependent questions. |
| 8 | Passport validity | `routing.passport_validity_months`, `documents.passport_copy_available` | Yes | Use passport validity as a qualification/review fact. |
| 9 | Health insurance / public insurance | `routing.health_insurance_status`, `documents.ccss_renewal_ready` | Pathway-specific | Ask whether the applicant has or will obtain qualifying coverage. |
| 10 | Criminal background | `routing.background_check_available`, `documents.police_clearance_available`, `routing.criminal_record_flag` | Yes when background affects status | Ask certificate availability and conviction disclosure as review facts. |
| 11 | Pathway-specific qualifications | `role.contractor.service_agreements_available`, `routing.no_work_authorization_acknowledged`, `routing.temporary_residence_acknowledged` | Pathway-specific | Include only when the requirement affects fit for the pathway. |
| 12 | Targeted supporting documents | `documents.civil_documents_available`, `documents.birth_certificate_available`, `documents.apostille_translation_ready` | Pathway-specific | Use sparingly; avoid turning the flow into a broad document checklist. |
| 13 | Final review notes | `routing.additional_information` | Optional | Capture edge cases after eligibility-critical questions. |
| 14 | Contact / consent | `identity.first_name`, `identity.last_name`, `phone`, `email`, `consent.*` | Surface/client-specific | Keep separate from eligibility logic where possible. |

## 3. Required Eligibility Categories

Every new pathway should explicitly decide whether each category is required, conditional, optional, or not applicable.

| Category | Default Decision | Why It Matters |
|---|---|---|
| Country | Required in Stage 1 | Routes to the correct pathway choices. |
| Pathway | Required in Stage 1 | Routes to the correct question file and rules module. |
| Work / income type | Required | Determines thresholds, evidence, and rule branches. |
| Foreign-source income | Required if destination-country income is restricted | Costa Rica DNV uses this as a hard eligibility condition. |
| Income amount | Required if financial threshold exists | Usually a hard eligibility rule. |
| Income evidence | Required or reviewable | Missing or weak evidence usually returns `needs_review`, not always `not_eligible`. |
| Income duration | Required if income continuity is required | Needed for duration-based rules and clarification copy. |
| Dependents | Conditional | Changes document requirements and may change income thresholds. |
| Nationality / residence | Usually required | Supports country-specific routing, residence facts, and review. |
| Passport validity | Required | Common qualification and review gate. |
| Health/public insurance | Required if legally relevant | May be initial eligibility, post-approval, or renewal-stage. |
| Criminal background | Required or reviewable | May affect eligibility or require legal review. |
| Pathway-specific qualifications | Conditional | Captures requirements unique to a visa or residence category. |
| Supporting documents | Pathway-specific | Include only when document status affects eligibility or review outcome. |
| Final review notes | Optional | Captures facts deterministic rules cannot classify. |

## 4. Qualification-First Style Rules

- Lead with facts that determine eligibility: work/income type, source, amount, evidence, duration, dependents, nationality, passport, health insurance, and background.
- Prefer Costa Rica DNV phrasing: short questions, concrete answer choices, and direct qualification facts.
- Avoid broad checklist prompts like “Are you ready to file?” or long document-preparation sequences unless the document status changes the outcome.
- Treat missing or uncertain supporting documents as `needs_review` unless the law or product decision makes them hard blockers.
- Keep post-approval or renewal questions only when they are necessary for the pathway’s eligibility/review logic.
- Do not add extra “readiness” categories to Costa Rica DNV to make it resemble newer pathways.

## 5. Optional Pathway-Specific Categories

Add these only when the pathway needs them.

- Service interest: Use `routing.service_interest` when one intake handles multiple products, such as visa plus tax services.
- Profession description: Use `role.profession_description` when professional activity needs review but does not fit a fixed choice list.
- Contractor service agreements: Use `role.contractor.service_agreements_available` when self-employed applicants need contracts or business-to-business proof.
- Pension source: Use `role.pensionado.pension_source_type` and `role.pensionado.pension_retirement_based` for pension/residency categories.
- Public insurance status: Use `routing.health_insurance_status` or country-specific equivalents such as `documents.ccss_renewal_ready`.
- Local receipt or conversion proof: Use a targeted field when the law requires funds to be received or converted locally.
- Consents: Use `consent.*` fields only for legal/client intake requirements, not eligibility logic.
- Marketing preference: Use `consent.marketing`; do not let it affect eligibility status.

## 6. Recommended Dotted-Key Naming Convention

Use stable, readable dotted keys so evaluator, rules, output, and exports can share payloads.

| Prefix | Use For | Examples |
|---|---|---|
| `routing.*` | Routing, high-level branching, applicant composition, acknowledgements | `routing.country`, `routing.pathway`, `routing.work_relationship`, `routing.applicant_type`, `routing.income_foreign_only` |
| `identity.*` | Applicant identity and residence facts | `identity.nationality`, `identity.country_of_residence`, `identity.first_name`, `identity.last_name` |
| `role.<work_type>.*` | Work-type-specific or income-type-specific eligibility facts | `role.contractor.monthly_income_usd`, `role.employee.income_evidence_types`, `role.pensionado.monthly_pension_usd` |
| `income.*` | Shared income fields not tied to one role | `income.gross_monthly_income_band_eur`, `income.income_history_months`, `income.income_evidence_types` |
| `documents.*` | Targeted document availability, evidence, legalization, or compliance facts | `documents.police_clearance_available`, `documents.birth_certificate_available`, `documents.apostille_translation_ready` |
| `consent.*` | Terms, privacy, judicial-data, and marketing consent | `consent.privacy_policy`, `consent.marketing` |

Naming rules:

- Use lowercase snake_case values and keys.
- Use currency suffixes for numeric income fields, such as `_usd` or `_eur`.
- Use `_months` for duration fields.
- Use `_available`, `_confirmed`, or `_acknowledged` when the value is a factual yes/no or status answer.
- Use `role.<work_type>.*` when rules differ by work type.
- Use `documents.*` only for targeted document facts that affect eligibility or review status.

## 7. Required Question Fields for `questions.json`

Every taxonomy field should include these properties unless there is a deliberate exception.

| Property | Required | Description |
|---|---|---|
| `key` | Yes | Dotted payload key where the answer is stored. |
| `depends_on` | Yes | List of prior field keys that should be answered before this field. Use `[]` for first pathway question. |
| `label` | Yes | User-facing prompt. |
| `input_type` | Yes | Common values: `text`, `number`, `choice`, `multi_choice`. |
| `required` | Yes | `true` for eligibility-critical fields; `false` for optional notes or metadata. |
| `choices` | Required for `choice` and `multi_choice` | Stable machine-readable values. |
| `description` | Optional | Helpful context that should not carry rule logic. |
| `applies_when` | Conditional | Use when a field should be asked only for certain prior answers. |
| `hidden` | Optional | Use sparingly. Hidden fields should not be relied on for required eligibility unless prefilled. |
| `typeform_field_id` / `typeform_ref` | Optional | Keep only for imported Typeform-backed pathways. |

## 8. Conditional Skip Rules

Questions should be skipped only when a previous answer makes them irrelevant or when the field is handled outside the backend flow.

Use `applies_when` for conditional questions:

- `equals`: Ask only when one field equals a value.
- `not_equals`: Ask unless one field equals a value.
- `contains`: Ask when a multi-choice answer includes a value.
- `not_contains`: Ask when a multi-choice answer does not include a value.

Recommended skip patterns:

- Skip dependent details unless the applicant is applying with dependents.
- Skip contractor-specific evidence unless `routing.work_relationship == contractor`.
- Skip employee-specific evidence unless `routing.work_relationship == employee`.
- Skip business-owner-specific evidence unless `routing.work_relationship == business_owner`.
- Skip DNV-only questions when `routing.service_interest` does not include `digital_nomad_visa`.
- Skip country/pathway fields inside `questions.json` when Stage 1 already captures `routing.country` and `routing.pathway`.

Avoid these skip patterns:

- Do not hide an eligibility-critical field unless it is guaranteed to be prefilled.
- Do not skip hard-failure fields because they are uncomfortable or legal-sensitive; ask them clearly and route to `needs_review` when appropriate.
- Do not mix contact/consent fields into eligibility order unless the intake surface requires those fields in the same backend flow.

## Implementation Checklist

Before adding a new pathway:

- Confirm Stage 1 country and pathway aliases.
- Use Costa Rica DNV as the model for question style and eligibility flow.
- Create `questions.json` in qualification-first backend order.
- Use dotted keys that match rule and output expectations.
- Mark every eligibility-critical field as `required: true`.
- Add `applies_when` to every conditional field.
- Decide each eligibility category as required, optional, conditional, or not applicable.
- Add tests for first question, eligible result, not-eligible hard failure, and needs-review document gap.
- Add output and clarification mappings for each failed requirement emitted by rules.
