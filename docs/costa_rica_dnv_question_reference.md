# Costa Rica DNV Question Reference

## Overview

This document captures the current Costa Rica Digital Nomad Visa question flow, answer choices, routing behavior, eligibility rules, clarification mappings, and output mappings.

- Pathway name: Costa Rica Digital Nomad Visa
- Canonical pathway ID: `costa_rica_dnv`
- Current aliases: `costa-rica-dnv`, `costa_rica_dnv`
- Default pathway: `costa_rica_dnv` when no pathway is provided
- Current implementation style: old shared taxonomy files
- Current shared taxonomy files:
  - `app/engine/taxonomies/taxonomy_contractor.json`
  - `app/engine/taxonomies/taxonomy_employee.json`
  - `app/engine/taxonomies/taxonomy_business_owner.json`
- New pathway folder usage: Costa Rica does not currently use a dedicated `app/engine/pathways/costa_rica_dnv/` folder. Spain DNV is the pathway currently using the new folder pattern.

## Current Routing

Costa Rica routing is resolved through `app/engine/pathway_registry.py`.

- `DEFAULT_PATHWAY_ID` is `costa_rica_dnv`.
- `resolve_pathway(None)` returns the default Costa Rica DNV pathway.
- `resolve_pathway("costa-rica-dnv")` and `resolve_pathway("costa_rica_dnv")` both resolve to canonical ID `costa_rica_dnv`.
- Costa Rica aliases use `behavior="current"` and `implemented=True`.
- Costa Rica has no `questions_file` and no `rules_module`, so navigation falls back to the old shared work-type taxonomy files and shared `app/engine/eligibility_rules.py`.

If no pathway has been selected yet, `app/engine/evaluator.py` first asks the stage-one selector questions:

| Order | Field Key | Prompt / Label | Input Type | Answer Choices | Required / Conditional | Applies When / Dependency Logic | Work Type |
|---:|---|---|---|---|---|---|---|
| S1 | `routing.country` | Which country are you interested in? | `choice` | `spain`, `costa_rica` | Required when no pathway is selected | Asked before work type if no selected pathway exists | Shared selector |
| S2 | `routing.pathway` | Which pathway would you like to check? | `choice` | For `costa_rica`: `costa_rica_dnv` | Required when no pathway is selected and country is known | Asked after `routing.country`; choices come from `PATHWAYS_BY_COUNTRY` | Shared selector |

The inline widget also has its own front-end country/pathway selector when no fixed `data-pathway` is configured. Its Costa Rica option value is `costa-rica-dnv`.

## Shared Routing Questions

These questions are shared across Costa Rica work types. `routing.work_relationship` and `routing.applicant_type` are hard gates in `app/engine/evaluator.py` before the work-type taxonomy loop. Some taxonomy files duplicate these fields with less metadata, but the runtime labels and choices below come from the evaluator hard gates.

| Order | Field Key | Prompt / Label | Input Type | Answer Choices | Required / Conditional | Applies When / Dependency Logic | Work Type |
|---:|---|---|---|---|---|---|---|
| 1 | `routing.work_relationship` | What best describes your work relationship? | `choice` | `contractor`, `employee`, `business_owner` | Required | Asked after stage-one selector when needed | Shared |
| 2 | `routing.applicant_type` | Are you applying as an individual or with family dependents? | `choice` | `individual`, `family` | Required | Asked after `routing.work_relationship` | Shared |

## Full Question List by Work Type

All fields are treated as required unless `required` is explicitly false. The current Costa Rica taxonomy files do not set `required=false`, so every listed field is required when its condition applies.

### Contractor

Source: `app/engine/taxonomies/taxonomy_contractor.json`

| Order | Field Key | Prompt / Label | Input Type | Answer Choices | Required / Conditional | Applies When / Dependency Logic | Work Type |
|---:|---|---|---|---|---|---|---|
| 1 | `routing.work_relationship` | What best describes your work relationship? | `choice` | `contractor`, `employee`, `business_owner` | Required | No dependency | Contractor / shared |
| 2 | `routing.applicant_type` | Are you applying as an individual or with family dependents? | `choice` | `individual`, `family` | Required | Depends on `routing.work_relationship` | Contractor / shared |
| 3 | `routing.income_foreign_only` | Is all of your income sourced from outside Costa Rica? | `choice` | `yes`, `no` | Required | Depends on `routing.work_relationship` | Contractor |
| 4 | `role.contractor.monthly_income_usd` | What is your gross monthly income (USD)? | `number` | None | Required | Depends on `routing.work_relationship` | Contractor |
| 5 | `role.contractor.income_evidence_types` | Which documents can you provide as proof of income? | `multi_choice` | `bank_statements`, `invoices`, `contracts`, `tax_returns`, `other` | Required | Depends on `routing.work_relationship` | Contractor |
| 6 | `role.contractor.income_evidence_months` | For how many months can you prove this income with those documents? | `choice` | `3`, `6`, `9`, `12` | Required | Depends on `role.contractor.income_evidence_types` | Contractor |
| 7 | `routing.dependents_count` | How many dependents are included in your application? | `number` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.applicant_type` | Contractor / family |
| 8 | `routing.dependent_relationships` | What is each dependent's relationship to you? | `text` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.dependents_count` | Contractor / family |
| 9 | `routing.dependent_ages` | What is the age of each dependent? | `text` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.dependents_count` | Contractor / family |
| 10 | `identity.nationality` | What is your nationality? | `text` | None | Required | No dependency | Contractor |
| 11 | `routing.passport_validity_months` | How many months will your passport be valid from your intended entry date? | `number` | None | Required | No dependency | Contractor |
| 12 | `routing.health_insurance_status` | Do you have qualifying health insurance for Costa Rica, or will you obtain it? | `choice` | `have_it`, `will_obtain` | Required | No dependency | Contractor |
| 13 | `routing.background_check_available` | Can you obtain a criminal background check from your country of residence? | `choice` | `yes`, `no` | Required | No dependency | Contractor |
| 14 | `routing.criminal_record_flag` | Do you have any criminal convictions that may appear on your background check? | `choice` | `yes`, `no` | Required | Depends on `routing.background_check_available` | Contractor |

### Employee

Source: `app/engine/taxonomies/taxonomy_employee.json`

| Order | Field Key | Prompt / Label | Input Type | Answer Choices | Required / Conditional | Applies When / Dependency Logic | Work Type |
|---:|---|---|---|---|---|---|---|
| 1 | `routing.work_relationship` | What best describes your work relationship? | `choice` | `contractor`, `employee`, `business_owner` | Required | Runtime hard gate before taxonomy loop | Employee / shared |
| 2 | `routing.applicant_type` | Are you applying as an individual or with family dependents? | `choice` | `individual`, `family` | Required | Runtime hard gate after `routing.work_relationship` | Employee / shared |
| 3 | `role.employee.monthly_income_usd` | What is your gross monthly salary (USD)? | `number` | None | Required | Depends on `routing.work_relationship` | Employee |
| 4 | `routing.income_foreign_only` | Is all of your income sourced from outside Costa Rica? | `choice` | `yes`, `no` | Required | Depends on `routing.work_relationship` | Employee |
| 5 | `role.employee.income_evidence_types` | Which documents can you provide as proof of income? | `multi_choice` | `bank_statements`, `pay_stubs`, `employment_contract`, `tax_returns`, `other` | Required | Depends on `routing.work_relationship` | Employee |
| 6 | `role.employee.income_evidence_months` | For how many months can you prove this income with those documents? | `choice` | `3`, `6`, `9`, `12` | Required | Depends on `role.employee.income_evidence_types` | Employee |
| 7 | `routing.dependents_count` | How many dependents are included in your application? | `number` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.applicant_type` | Employee / family |
| 8 | `routing.dependent_relationships` | What is each dependent's relationship to you? | `text` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.dependents_count` | Employee / family |
| 9 | `routing.dependent_ages` | What is the age of each dependent? | `text` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.dependents_count` | Employee / family |
| 10 | `identity.nationality` | What is your nationality? | `text` | None | Required | No dependency | Employee |
| 11 | `routing.passport_validity_months` | How many months will your passport be valid from your intended entry date? | `number` | None | Required | No dependency | Employee |
| 12 | `routing.health_insurance_status` | Do you have qualifying health insurance for Costa Rica, or will you obtain it? | `choice` | `have_it`, `will_obtain` | Required | No dependency | Employee |
| 13 | `routing.background_check_available` | Can you obtain a criminal background check from your country of residence? | `choice` | `yes`, `no` | Required | No dependency | Employee |
| 14 | `routing.criminal_record_flag` | Do you have any criminal convictions that may appear on your background check? | `choice` | `yes`, `no` | Required | Depends on `routing.background_check_available` | Employee |

### Business Owner

Source: `app/engine/taxonomies/taxonomy_business_owner.json`

| Order | Field Key | Prompt / Label | Input Type | Answer Choices | Required / Conditional | Applies When / Dependency Logic | Work Type |
|---:|---|---|---|---|---|---|---|
| 1 | `routing.work_relationship` | What best describes your work relationship? | `choice` | `contractor`, `employee`, `business_owner` | Required | Runtime hard gate before taxonomy loop | Business owner / shared |
| 2 | `routing.applicant_type` | Are you applying as an individual or with family dependents? | `choice` | `individual`, `family` | Required | Runtime hard gate after `routing.work_relationship` | Business owner / shared |
| 3 | `role.business_owner.monthly_income_usd` | What is your average gross monthly business income (USD)? | `number` | None | Required | Depends on `routing.work_relationship` | Business owner |
| 4 | `routing.income_foreign_only` | Is all of your income sourced from outside Costa Rica? | `choice` | `yes`, `no` | Required | Depends on `routing.work_relationship` | Business owner |
| 5 | `role.business_owner.income_evidence_types` | Which documents can you provide as proof of your business income? | `multi_choice` | `bank_statements`, `tax_returns`, `profit_loss_statements` | Required | Depends on `routing.work_relationship` | Business owner |
| 6 | `role.business_owner.income_evidence_months` | For how many months can you prove this income with those documents? | `choice` | `3`, `6`, `9`, `12` | Required | Depends on `role.business_owner.income_evidence_types` | Business owner |
| 7 | `routing.dependents_count` | How many dependents are included in your application? | `number` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.applicant_type` | Business owner / family |
| 8 | `routing.dependent_relationships` | What is each dependent's relationship to you? | `text` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.dependents_count` | Business owner / family |
| 9 | `routing.dependent_ages` | What is the age of each dependent? | `text` | None | Conditional | Applies when `routing.applicant_type == family`; depends on `routing.dependents_count` | Business owner / family |
| 10 | `identity.nationality` | What is your nationality? | `text` | None | Required | No dependency | Business owner |
| 11 | `routing.passport_validity_months` | How many months will your passport be valid from your intended entry date? | `number` | None | Required | No dependency | Business owner |
| 12 | `routing.health_insurance_status` | Do you have qualifying health insurance for Costa Rica, or will you obtain it? | `choice` | `have_it`, `will_obtain` | Required | No dependency | Business owner |
| 13 | `routing.background_check_available` | Can you obtain a criminal background check from your country of residence? | `choice` | `yes`, `no` | Required | No dependency | Business owner |
| 14 | `routing.criminal_record_flag` | Do you have any criminal convictions that may appear on your background check? | `choice` | `yes`, `no` | Required | Depends on `routing.background_check_available` | Business owner |

## Eligibility Rules

Source: `app/engine/eligibility_rules.py` and `app/engine/evidence_validation.py`

Final status resolution:

- `eligible`: no failed requirements.
- `needs_review`: failed requirements exist, but none are hard failures.
- `not_eligible`: at least one hard failure exists.

Hard failures are `income_amount`, `income_duration_months`, `foreign_income`, and `passport_validity`.

| Rule Name | Field Key Used | Pass Condition | Fail Condition | Failed Requirement Key | Outcome Status |
|---|---|---|---|---|---|
| Minimum monthly income | Contractor: `role.contractor.monthly_income_usd`; employee: `role.employee.monthly_income_usd`; business owner: `role.business_owner.monthly_income_usd` | Numeric monthly income is at least `3000` USD | Missing, nonnumeric, or below `3000` | `income_amount` | `not_eligible` if this hard failure exists |
| Income duration | Contractor: `role.contractor.income_evidence_months`; employee: `role.employee.income_evidence_months`; business owner: `role.business_owner.income_evidence_months` | Integer months is at least `12` | Missing, nonnumeric, or below `12` | `income_duration_months` | `not_eligible` if this hard failure exists |
| Contractor income evidence | `role.contractor.income_evidence_types` | Includes all required evidence: `bank_statements`, `invoices`, `contracts`, `tax_returns` | Missing any required evidence type | Missing evidence keys, such as `bank_statements`, `invoices`, `contracts`, `tax_returns` | `needs_review` if no hard failures also exist |
| Employee income evidence | `role.employee.income_evidence_types` | Current list payload includes `bank_statements`, `pay_stubs`, `employment_contract`, `tax_returns` | Missing any required employee evidence. Note: base evidence validation requires `pay_stubs` and `bank_statements`; `eligibility_rules.py` adds the full employee list when the payload is a list. | Missing evidence keys, such as `bank_statements`, `pay_stubs`, `employment_contract`, `tax_returns` | `needs_review` if no hard failures also exist |
| Business owner income evidence | `role.business_owner.income_evidence_types` | Includes all required evidence: `bank_statements`, `tax_returns`, `profit_loss_statements` | Missing any required evidence type | Missing evidence keys, such as `bank_statements`, `tax_returns`, `profit_loss_statements` | `needs_review` if no hard failures also exist |
| Foreign-source income | `routing.income_foreign_only` | Value is exactly `yes` | Value is missing or not `yes` | `foreign_income` | `not_eligible` if this hard failure exists |
| Passport validity | `routing.passport_validity_months` | Integer months is at least `6` | Missing, nonnumeric, zero, or below `6` | `passport_validity` | `not_eligible` if this hard failure exists |
| Background check availability | `routing.background_check_available` | Current evaluator asks the question, but eligibility rule does not append a failure for `no` | No direct eligibility failure is currently appended | None currently | No direct status effect; final status depends on other rules |
| Criminal record flag | `routing.criminal_record_flag` | Current evaluator asks the question, but eligibility rule does not append a failure for `yes` | No direct eligibility failure is currently appended | None currently | No direct status effect; output may still show criminal-background clarification once answered |
| Health insurance status | `routing.health_insurance_status` | Asked as an intake question | No eligibility rule currently evaluates this field | None currently | No direct status effect |
| Dependents | `routing.applicant_type`, `routing.dependents_count`, `routing.dependent_relationships`, `routing.dependent_ages` | Family-only dependent questions are completed when applicable | No eligibility rule currently evaluates dependent count, ages, or relationships | None currently | No direct status effect |

## Clarifications

Clarifications are assembled by `app/engine/output_builder.py` from `app/taxonomies/clarification/`.

Behavior notes:

- Criminal background clarification is always shown once `routing.background_check_available` or `routing.criminal_record_flag` exists in routing, whether the applicant answered yes or no.
- For `needs_review` and `not_eligible`, work-type clarification entries are included when their `requirement` matches a failed requirement.
- For `not_eligible`, hard-failure clarification entries have alternative or secondary evidence removed.
- For `not_eligible` plus `income_duration_months`, `output_builder.py` currently overrides the clarification text with: `Costa Rica's Digital Nomad visa requires proof of stable business income for at least 12 consecutive months. This is a mandatory requirement with no exceptions.`

### Contractor Clarifications

Source: `app/taxonomies/clarification/taxonomy_clarification_contractor.json`

| Failed Requirement | Clarification Title | Clarification Text / Behavior |
|---|---|---|
| `tax_returns` | Tax Returns | When formal tax returns are unavailable, authorities may accept alternative evidence that demonstrates income amount, source, and continuity. Secondary evidence includes CPA/accountant income summary letter, year-end income statements, and platform annual payout summaries. |
| `invoices` | Invoices | When formal invoices are unavailable, authorities may accept alternative evidence showing services rendered, payment terms, and income continuity. Secondary evidence includes signed contracts, client confirmation letters, and platform work records. |
| `contracts` | Contracts | When formal contracts are unavailable, authorities may accept alternative evidence showing an ongoing work relationship and income generation. Secondary evidence includes invoices, client confirmation letters, and platform contracts or profiles. |
| `income_duration_months` | Income History Duration | Costa Rica's DNV requires at least 12 months of documented income. Runtime `not_eligible` output replaces this text with the hard-failure mandatory-requirement text noted above. |
| `bank_statements` | None currently | Required by evidence validation, but no contractor clarification entry currently exists. |
| `income_amount` | None currently | Hard failure exists, but no contractor clarification entry currently exists. |
| `foreign_income` | None currently | Hard failure exists, but no contractor clarification entry currently exists. |
| `passport_validity` | None currently | Hard failure exists, but no contractor clarification entry currently exists. |

### Employee Clarifications

Source: `app/taxonomies/clarification/taxonomy_clarification_employee.json`

| Failed Requirement | Clarification Title | Clarification Text / Behavior |
|---|---|---|
| `income_duration_months` | Income History Duration | Costa Rica's DNV requires proof of income continuity for at least 12 months. Runtime `not_eligible` output replaces this text with the hard-failure mandatory-requirement text noted above. |
| `bank_statements` | Bank Statements | Bank statements verify deposits and consistent receipt of income. |
| `pay_stubs` | Pay Stubs | Pay stubs verify employment-based income and should show name, employer, pay dates, and gross pay. |
| `tax_returns` | Tax Returns | When tax returns are unavailable, alternative evidence may include an employer income summary letter or year-end salary statements. |
| `employment_contract` | Employment Contract / Letter | When a formal employment contract or offer letter is unavailable, alternative confirmation may include an employer confirmation letter. |
| `income_amount` | Income Amount - Minimum Monthly Income | Reported income does not meet the minimum threshold. Suggested next steps are to recheck gross/net income, average variable compensation, or recognize that the amount may not qualify. |
| `foreign_income` | Foreign Income - Employer and Pay Source Must Be Outside Costa Rica | Income must be earned from sources outside Costa Rica; confirm employer and salary payments are outside Costa Rica. |
| `passport_validity` | Passport Validity - Expiration Window | Passport appears to expire too soon; renew before applying and re-run the check. |
| `criminal_background` | Criminal Background - Police Clearance | Present in employee clarification taxonomy, but current eligibility rules do not emit `criminal_background`; the shared all-work-types criminal clarification is the active runtime path. |

### Business Owner Clarifications

Source: `app/taxonomies/clarification/taxonomy_clarification_business_owner.json`

| Failed Requirement | Clarification Title | Clarification Text / Behavior |
|---|---|---|
| `tax_returns` | Tax Returns | When business tax returns are unavailable, alternative evidence may include CPA/accountant income summary letter, year-end financial statements, or business bank statements showing revenue. |
| `profit_loss_statements` | Profit & Loss Statements | When formal P&L statements are unavailable, alternative evidence may include accountant-prepared financial summaries, business bank statements, or accounting software reports. |
| `bank_statements` | Bank Statements | When business bank statements are unavailable or incomplete, alternative evidence may include payment processor statements or accountant-verified income confirmation. |
| `income_duration_months` | Income Duration - 12-Month Requirement | Requires stable business income for at least 12 consecutive months. Runtime `not_eligible` output replaces this text with the hard-failure mandatory-requirement text noted above. |
| `income_amount` | Income Amount - Minimum Monthly Income | Reported business income does not meet the minimum threshold. Suggested next steps are to recheck income, average seasonal income, or recognize that the amount may not qualify. |
| `foreign_income` | Foreign Income - Business Revenue Must Be Earned Outside Costa Rica | Qualifying business revenue must be earned outside Costa Rica. Mixed revenue may require proof that foreign-sourced income meets the threshold. |
| `passport_validity` | Passport Validity - Expiration Window | Passport appears to expire too soon; renew before applying and re-run the check. |

### Shared Criminal Background Clarification

Source: `app/taxonomies/clarification/taxonomy_clarification_background.json`

| Trigger | Requirement | Title | Clarification Text / Behavior |
|---|---|---|---|
| `routing.background_check_available` answered or `routing.criminal_record_flag` answered | `criminal_background` | Criminal Background - Police Clearance | Costa Rica requires an official police clearance certificate from the country of nationality and recent residence. Criminal background information is handled case by case, and legal guidance is required if a record exists. |

## Output Mapping

Sources:

- `app/taxonomies/output/taxonomy_output_meta.json`
- `app/taxonomies/output/taxonomy_output_summary.json`
- `app/taxonomies/output/taxonomy_output_cta.json`
- `app/engine/output_builder.py`

### Eligible

| Output Area | Current Value |
|---|---|
| Meta status | `eligible` |
| Meta fields | `status`, `work_type`, `visa_type` |
| Summary | `Based on the information provided, you meet the eligibility requirements.` |
| Clarifications | Empty unless criminal background fields have been answered, in which case shared criminal clarification is included. |
| CTA text | `If you would like assistance preparing or reviewing your application, professional support is available.` |
| CTA action label | `Book a consultation with Great Expatations` |

### Needs Review

| Output Area | Current Value |
|---|---|
| Meta status | `needs_review` |
| Meta fields | `status`, `work_type`, `visa_type` |
| Summary | `Eligibility cannot be confirmed yet due to pending verification.` |
| Clarifications | Matching failed evidence requirements plus shared criminal clarification if criminal fields were answered. |
| CTA text | `If you would like assistance addressing the pending requirements, professional support is available.` and `Services may include document review, application preparation, and legal consultation.` |
| CTA action label | `Book a consultation with Great Expatations` |

### Not Eligible

| Output Area | Current Value |
|---|---|
| Meta status | `not_eligible` |
| Meta fields | `status`, `work_type`, `visa_type` |
| Summary | Currently blank for Costa Rica because shared output taxonomy variants use `ineligible`, while the rules return `not_eligible`. |
| Clarifications | Matching failed requirements. Hard-failure alternatives are stripped, and `income_duration_months` text is overridden with a mandatory-requirement statement. Shared criminal clarification is included if criminal fields were answered. |
| CTA text | Fallback from `output_builder.py`: `Unfortunately, you do not currently meet the mandatory requirements for Costa Rica's Digital Nomad visa.` and `If your situation changes in the future, you may reapply once all requirements are satisfied.` |
| CTA action label | None in the fallback block. |

## Reference Checklist: Questions Every New Visa Pathway Should Consider

Use Costa Rica DNV as the baseline. Every future pathway should decide whether each item is asked, where it is routed, how it is validated, and how failed answers affect output.

- Work type: What applicant categories exist, and do they change question order, evidence requirements, or thresholds?
- Income amount: What exact amount is required, in what currency, and does it vary for individuals versus families?
- Income duration: How many months of income history are required, and must they be consecutive?
- Income evidence: Which documents are sufficient, which are optional, and which missing documents trigger review instead of ineligibility?
- Foreign-source income: Must income be earned outside the destination country, and how is mixed-source income handled?
- Passport validity: What minimum validity window is required from the intended entry or application date?
- Criminal/background issue: Is police clearance required, and do disclosures trigger review, ineligibility, or attorney review?
- Health insurance if relevant: Is insurance required at intake, only before approval, or not part of eligibility?
- Dependents: Are dependents allowed, which relationships qualify, and do they change income thresholds or required documents?
- Documentation availability: Which missing documents have accepted secondary evidence and which are hard blockers?
- Country/residency factors: Are nationality, residence, tax residence, local presence, or consular filing location relevant?
- Final CTA/outcome: What summary, clarification, and next-step CTA should appear for `eligible`, `needs_review`, and `not_eligible`?
