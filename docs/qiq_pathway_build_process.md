# QIQ Pathway Build Process

## Purpose

Use this process when adding a new QIQ visa or residency pathway.

Costa Rica DNV is the reference model for QIQ question style and eligibility structure. QIQ is an eligibility/qualification engine, not an application-readiness checklist. New pathways should ask qualification-first questions that determine `eligible`, `needs_review`, or `not_eligible`; they should not become broad filing-preparation or document-readiness checklists.

## Reference Model

Use Costa Rica DNV as the baseline because it has the core QIQ structure:

- Work or income type determines the rule branch.
- Foreign-source income is asked as a qualification fact.
- Income amount is a core hard-gate requirement.
- Income evidence and income duration support eligibility or review.
- Dependents are conditional.
- Passport, health insurance, and criminal background are qualification/review facts.
- Outputs and clarifications map directly to failed requirements.

Do not refactor Costa Rica DNV to match newer pathways. Align newer pathways toward Costa Rica DNV’s qualification-first style.

## 1. Create Requirements Reference

Create a source reference before writing pathway logic.

Files:

- `app/engine/pathways/<pathway_id>/requirements_reference.csv`
- `app/engine/pathways/<pathway_id>/requirements_reference.md`

Preserve:

- Requirement category
- Requirement
- Exact eligibility rule
- Evidence required when it affects qualification/review
- Status, such as mandatory, conditional, discretionary, or reviewable
- Official source URL

The markdown file should be human-readable and should distinguish hard eligibility gates from review-only requirements.

## 2. Create Pathway Folder

Create one folder per pathway:

```text
app/engine/pathways/<pathway_id>/
```

Use lowercase snake_case for the canonical pathway ID, for example:

- `spain_dnv`
- `costa_rica_pensionado`

Keep all pathway-specific files in that folder.

## 3. Create `questions.json`

Create:

```text
app/engine/pathways/<pathway_id>/questions.json
```

Follow the Costa Rica DNV qualification-first order:

1. Work / income type
2. Foreign-source income
3. Income amount
4. Income evidence
5. Income duration
6. Dependents, conditional
7. Nationality / residence
8. Passport validity
9. Health insurance / public insurance
10. Criminal background
11. Pathway-specific qualification facts
12. Targeted supporting documents only when they affect outcome
13. Final review notes, optional
14. Contact / consent only when the surface requires it

Each question should include:

- `key`
- `depends_on`
- `label`
- `input_type`
- `required`
- `choices` for `choice` or `multi_choice`
- `applies_when` for conditional questions

Use dotted keys consistently, such as:

- `routing.*`
- `identity.*`
- `role.<work_type>.*`
- `income.*`
- `documents.*`
- `consent.*`

Avoid broad checklist prompts. A document question belongs in `questions.json` only when the answer changes eligibility, review status, or pathway routing.

## 4. Create `rules.py`

Create:

```text
app/engine/pathways/<pathway_id>/rules.py
```

Rules should:

- Accept the payload collected by `questions.json`.
- Evaluate hard failures as `not_eligible`.
- Evaluate uncertain, missing, or reviewable issues as `needs_review`.
- Return `eligible` only when no hard failure or review requirement remains.
- Emit stable failed requirement keys that exactly match `clarifications.json`.

Recommended result shape:

```python
{
    "eligibility_status": "eligible",
    "failed_requirements": [],
    "pathway": "<pathway_id>",
    "visa_type": "<Human Visa Name>",
}
```

Keep rules deterministic. Do not use rule logic to collect filing-readiness checklist items unless they affect qualification or review.

## 5. Create `output.json`

Create:

```text
app/engine/pathways/<pathway_id>/output.json
```

Map pathway outcomes to user-facing summaries and CTAs:

- `eligible`
- `needs_review`
- `not_eligible`

Outputs should explain the qualification result, not pretend to approve an application. Keep CTAs aligned with the status, such as consultation, email follow-up, or alternative options.

## 6. Create `clarifications.json`

Create:

```text
app/engine/pathways/<pathway_id>/clarifications.json
```

Every failed requirement emitted by `rules.py` should have a clarification entry:

- `requirement`
- `title`
- `clarification`

Clarification text should explain why the requirement matters and what kind of review is needed. It should not become a full application-preparation checklist.

## 7. Register Pathway Aliases

Register the canonical pathway and aliases in the pathway registry.

Use stable aliases such as:

- `<country>-<pathway>`
- `<country>_<pathway>`

Wire the registry entry to:

- `questions.json`
- `rules.py`
- `output.json`
- `clarifications.json`

Confirm the pathway resolves from both dashed and underscored aliases.

## 8. Add Widget Selector Option

Add the pathway to the inline widget Stage 1 selector.

The selector should:

- Show the option only under the correct country.
- Use a human-readable label.
- Submit the canonical or registered alias expected by the backend.

Do not change unrelated country options, production embed settings, or the full chat window unless explicitly required.

## 9. Add Tests

Add or update tests for:

- Alias resolution
- First backend question
- Happy-path `eligible`
- Hard-failure `not_eligible`
- Reviewable-gap `needs_review`
- Output summary and CTA mapping
- Clarification mapping for each failed requirement
- Widget or Stage 1 routing when selector behavior changes

Prefer focused tests for the new pathway and avoid changing existing Costa Rica DNV behavior.

## 10. Browser-Test Inline Widget

After automated tests pass, browser-test the inline widget locally.

Check:

- Stage 1 country selector shows the pathway option.
- The selected pathway routes to the expected first backend question.
- Requests go to the intended local API base.
- CORS preflight succeeds for local development origins.
- The flow reaches `eligible`, `needs_review`, and `not_eligible` outcomes.
- CTA and clarification copy appears for each outcome.

Local example:

```text
Widget:  http://127.0.0.1:5500/widget/
Backend: http://127.0.0.1:<api_port>
```

## Final Pre-Launch Checklist

- Requirements reference exists and cites sources.
- Pathway folder contains `questions.json`, `rules.py`, `output.json`, and `clarifications.json`.
- Questions follow Costa Rica DNV’s qualification-first style.
- No broad application-readiness checklist has been added.
- Rule failure keys match clarification requirements.
- Aliases resolve correctly.
- Inline widget selector shows the new pathway.
- Automated tests pass.
- Inline widget browser test passes locally.
