"""Tests for scripts/audit_pathway_quality.py.

These are fixture-based: each test builds a tiny synthetic pathway
directory (questions.json / rules.py / clarifications.json / output.json)
under a pytest tmp_path, points the audit module at it via monkeypatch, and
asserts on the resulting findings. This keeps the tests independent of the
real (evolving) pathway content under app/engine/pathways/, except for the
one integration test at the bottom, which deliberately audits the real repo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from scripts import audit_pathway_quality as audit_mod


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _default_field(**overrides) -> Dict[str, Any]:
    field = {
        "key": "routing.work_relationship",
        "depends_on": [],
        "label": "How do you work?",
        "input_type": "choice",
        "required": True,
        "choices": ["employee", "contractor"],
    }
    field.update(overrides)
    return field


DEFAULT_RULES_SOURCE = '''
HARD_FAILURES = {"income_below_minimum"}


def _get_dotted(payload, key, default=None):
    current = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_eligibility(payload):
    failed = []
    work_relationship = _get_dotted(payload, "routing.work_relationship")
    income = _as_float(_get_dotted(payload, "financial.monthly_income_eur"))
    if income is None or income < 2000:
        failed.append("income_below_minimum")

    status = "not_eligible" if any(r in HARD_FAILURES for r in failed) else (
        "needs_review" if failed else "eligible"
    )
    return {
        "eligibility_status": status,
        "failed_requirements": failed,
        "pathway": "fixture_pathway",
        "work_type": work_relationship,
    }
'''

DEFAULT_CLARIFICATIONS = {
    "pathway": "fixture_pathway",
    "clarifications": [
        {
            "requirement": "income_below_minimum",
            "title": "Income Below Minimum",
            "clarification": "Monthly income is below the required minimum.",
        }
    ],
}

DEFAULT_OUTPUT = {
    "pathway": "fixture_pathway",
    "summary_statement": {
        "variants": {
            "eligible": {"text": "You may be eligible."},
            "needs_review": {"text": "Needs review."},
            "not_eligible": {"text": "Not eligible."},
        },
        "requirement_variants": {
            "income_below_minimum": {"text": "Income is below the minimum."}
        },
    },
    "next_steps_cta": {
        "variants": {
            "eligible": {"enabled": True, "text": ["Book a consultation."], "action": {"label": "Book", "type": "consultation"}},
        },
        "requirement_variants": {},
    },
}


def write_pathway(
    tmp_path: Path,
    name: str,
    *,
    fields: Optional[List[Dict[str, Any]]] = None,
    rules_source: Optional[str] = None,
    clarifications: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
    post_eligibility_checklist: Optional[Dict[str, Any]] = None,
    write_requirements_reference: bool = False,
) -> Path:
    """Write a minimal, self-contained pathway fixture and return its dir."""
    pathway_dir = tmp_path / name
    pathway_dir.mkdir(parents=True, exist_ok=True)

    if fields is None:
        fields = [
            _default_field(),
            {
                "key": "financial.monthly_income_eur",
                "depends_on": ["routing.work_relationship"],
                "label": "What is your monthly income in EUR?",
                "input_type": "number",
                "required": True,
            },
        ]

    questions_data: Dict[str, Any] = {
        "pathway": name,
        "taxonomy_fields": fields,
    }
    if post_eligibility_checklist is not None:
        questions_data["post_eligibility_checklist"] = post_eligibility_checklist

    (pathway_dir / "questions.json").write_text(json.dumps(questions_data, indent=2), encoding="utf-8")
    (pathway_dir / "rules.py").write_text(
        rules_source if rules_source is not None else DEFAULT_RULES_SOURCE, encoding="utf-8"
    )
    (pathway_dir / "clarifications.json").write_text(
        json.dumps(clarifications if clarifications is not None else DEFAULT_CLARIFICATIONS, indent=2),
        encoding="utf-8",
    )
    (pathway_dir / "output.json").write_text(
        json.dumps(output if output is not None else DEFAULT_OUTPUT, indent=2), encoding="utf-8"
    )
    if write_requirements_reference:
        (pathway_dir / "requirements_reference.md").write_text(
            "# Fixture Requirements Reference\n\n## Income\n\nMinimum monthly income applies.\n",
            encoding="utf-8",
        )

    return pathway_dir


@pytest.fixture()
def pathways_root(tmp_path, monkeypatch):
    root = tmp_path / "pathways"
    root.mkdir()
    monkeypatch.setattr(audit_mod, "PATHWAYS_DIR", root)
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(audit_mod, "REPORT_DIR", reports_dir)
    return root


def _rule_messages(audit: audit_mod.PathwayAudit, rule: str) -> List[str]:
    return [f.message for f in audit.findings if f.rule == rule]


def _has_finding(audit: audit_mod.PathwayAudit, rule: str, severity: Optional[str] = None) -> bool:
    return any(
        f.rule == rule and (severity is None or f.severity == severity)
        for f in audit.findings
    )


# ---------------------------------------------------------------------------
# 1. not_sure / escape choice detection
# ---------------------------------------------------------------------------


def test_not_sure_detection(pathways_root):
    write_pathway(
        pathways_root,
        "fixture_escape",
        fields=[
            _default_field(),
            {
                "key": "financial.monthly_income_eur",
                "depends_on": ["routing.work_relationship"],
                "label": "What is your monthly income in EUR?",
                "input_type": "number",
                "required": True,
            },
            {
                "key": "routing.health_insurance_status",
                "depends_on": ["financial.monthly_income_eur"],
                "label": "Do you have health insurance?",
                "input_type": "choice",
                "required": True,
                "choices": ["yes", "no", "not_sure"],
            },
        ],
    )

    audit = audit_mod.audit_pathway("fixture_escape")

    assert _has_finding(audit, "escape_choices", "FAIL")
    assert audit.status == "FAIL"
    assert any("not_sure" in m for m in _rule_messages(audit, "escape_choices"))


def test_escape_choice_variants_detected(pathways_root):
    """not_ready / unknown / unsure / maybe should all trip the same rule."""
    for bad_choice in ("not_ready", "unknown", "unsure", "maybe"):
        write_pathway(
            pathways_root,
            "fixture_escape_variant",
            fields=[
                _default_field(choices=["yes", "no", bad_choice]),
                {
                    "key": "financial.monthly_income_eur",
                    "depends_on": ["routing.work_relationship"],
                    "label": "What is your monthly income in EUR?",
                    "input_type": "number",
                    "required": True,
                },
            ],
            rules_source=DEFAULT_RULES_SOURCE.replace(
                '_get_dotted(payload, "routing.work_relationship")',
                '_get_dotted(payload, "routing.work_relationship")',
            ),
        )
        audit = audit_mod.audit_pathway("fixture_escape_variant")
        assert _has_finding(audit, "escape_choices", "FAIL"), f"expected FAIL for choice {bad_choice!r}"


def test_post_eligibility_checklist_choices_are_not_inspected(pathways_root):
    """not_sure inside post_eligibility_checklist should NOT fail -- only the
    live taxonomy_fields flow is in scope for the escape-choice rule."""
    write_pathway(
        pathways_root,
        "fixture_checklist_escape",
        post_eligibility_checklist={
            "fields": [
                {
                    "key": "compliance.some_acknowledgement",
                    "label": "Do you understand X?",
                    "input_type": "choice",
                    "choices": ["yes", "no", "not_sure"],
                }
            ]
        },
    )

    audit = audit_mod.audit_pathway("fixture_checklist_escape")

    assert not _has_finding(audit, "escape_choices")


# ---------------------------------------------------------------------------
# 2. contact / sales / consent detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "identity.first_name",
        "identity.last_name",
        "contact.phone",
        "contact.email",
        "consent.terms_conditions",
        "consent.privacy_policy",
        "consent.marketing",
        "routing.service_interest",
        "routing.meeting_scheduler",
    ],
)
def test_contact_sales_field_detection(pathways_root, key):
    write_pathway(
        pathways_root,
        "fixture_contact",
        fields=[
            _default_field(),
            {
                "key": "financial.monthly_income_eur",
                "depends_on": ["routing.work_relationship"],
                "label": "What is your monthly income in EUR?",
                "input_type": "number",
                "required": True,
            },
            {
                "key": key,
                "depends_on": [],
                "label": "Please provide this information.",
                "input_type": "text",
                "required": True,
            },
        ],
    )

    audit = audit_mod.audit_pathway("fixture_contact")

    assert _has_finding(audit, "contact_sales_consent", "FAIL"), f"expected FAIL for key {key!r}"
    assert audit.status == "FAIL"


def test_contact_field_allowlist_suppresses_finding(pathways_root, monkeypatch):
    monkeypatch.setitem(
        audit_mod.CONTACT_SALES_ALLOWLIST, "fixture_allowlisted", {"identity.email"}
    )
    write_pathway(
        pathways_root,
        "fixture_allowlisted",
        fields=[
            _default_field(),
            {
                "key": "financial.monthly_income_eur",
                "depends_on": ["routing.work_relationship"],
                "label": "What is your monthly income in EUR?",
                "input_type": "number",
                "required": True,
            },
            {
                "key": "identity.email",
                "depends_on": [],
                "label": "Email",
                "input_type": "text",
                "required": True,
            },
        ],
    )

    audit = audit_mod.audit_pathway("fixture_allowlisted")

    assert not _has_finding(audit, "contact_sales_consent")


# ---------------------------------------------------------------------------
# 3. phantom rule field detection
# ---------------------------------------------------------------------------


def test_phantom_rule_field_detection(pathways_root):
    rules_source = '''
HARD_FAILURES = {"income_below_minimum"}


def _get_dotted(payload, key, default=None):
    current = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def evaluate_eligibility(payload):
    failed = []
    _get_dotted(payload, "routing.work_relationship")
    income = _get_dotted(payload, "financial.monthly_income_eur")
    _get_dotted(payload, "financial.this_key_does_not_exist")
    if income is None:
        failed.append("income_below_minimum")
    status = "not_eligible" if failed else "eligible"
    return {"eligibility_status": status, "failed_requirements": failed, "pathway": "fixture"}
'''
    write_pathway(pathways_root, "fixture_phantom", rules_source=rules_source)

    audit = audit_mod.audit_pathway("fixture_phantom")

    assert _has_finding(audit, "phantom_rule_key", "FAIL")
    assert any(
        "financial.this_key_does_not_exist" in m for m in _rule_messages(audit, "phantom_rule_key")
    )
    assert audit.status == "FAIL"


def test_no_phantom_key_when_all_reads_exist(pathways_root):
    write_pathway(pathways_root, "fixture_no_phantom")

    audit = audit_mod.audit_pathway("fixture_no_phantom")

    assert not _has_finding(audit, "phantom_rule_key", "FAIL")


# ---------------------------------------------------------------------------
# 4. unused question flagging
# ---------------------------------------------------------------------------


def test_unused_question_flagging(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
        {
            "key": "routing.never_referenced_field",
            "depends_on": ["financial.monthly_income_eur"],
            "label": "This question is never read by rules.py.",
            "input_type": "choice",
            "required": True,
            "choices": ["yes", "no"],
        },
    ]
    write_pathway(pathways_root, "fixture_unused", fields=fields)

    audit = audit_mod.audit_pathway("fixture_unused")

    assert _has_finding(audit, "unused_question_key", "WARN")
    assert any(
        "routing.never_referenced_field" in m for m in _rule_messages(audit, "unused_question_key")
    )
    # Unused questions are a WARN, never a FAIL, and never silently dropped.
    assert not any(
        f.rule == "unused_question_key" and f.severity == "FAIL" for f in audit.findings
    )


def test_optional_field_not_flagged_as_unused(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
        {
            "key": "routing.additional_information",
            "depends_on": ["financial.monthly_income_eur"],
            "label": "Anything else we should know?",
            "input_type": "text",
            "required": False,
        },
    ]
    write_pathway(pathways_root, "fixture_optional_unused", fields=fields)

    audit = audit_mod.audit_pathway("fixture_optional_unused")

    assert not any(
        f.location == "routing.additional_information" for f in audit.findings if f.rule == "unused_question_key"
    )


# ---------------------------------------------------------------------------
# 5. dead clarification / output code detection
# ---------------------------------------------------------------------------


def test_dead_clarification_code_detection(pathways_root):
    clarifications = {
        "pathway": "fixture_dead",
        "clarifications": [
            {
                "requirement": "income_below_minimum",
                "title": "Income Below Minimum",
                "clarification": "Below minimum.",
            },
            {
                "requirement": "this_code_is_never_emitted",
                "title": "Dead Entry",
                "clarification": "This can never actually appear.",
            },
        ],
    }
    write_pathway(pathways_root, "fixture_dead", clarifications=clarifications)

    audit = audit_mod.audit_pathway("fixture_dead")

    assert _has_finding(audit, "dead_requirement_code", "WARN")
    assert any(
        "this_code_is_never_emitted" in m for m in _rule_messages(audit, "dead_requirement_code")
    )


def test_dead_output_variant_detection(pathways_root):
    output = json.loads(json.dumps(DEFAULT_OUTPUT))
    output["summary_statement"]["requirement_variants"]["this_output_code_is_dead"] = {
        "text": "Never shown."
    }
    write_pathway(pathways_root, "fixture_dead_output", output=output)

    audit = audit_mod.audit_pathway("fixture_dead_output")

    assert any(
        "this_output_code_is_dead" in m for m in _rule_messages(audit, "dead_requirement_code")
    )


def test_stage_annotated_dead_code_is_noted_as_intentional(pathways_root):
    clarifications = {
        "pathway": "fixture_stage",
        "clarifications": [
            {
                "requirement": "income_below_minimum",
                "title": "Income Below Minimum",
                "clarification": "Below minimum.",
            },
            {
                "requirement": "preserved_for_later",
                "title": "Preserved",
                "clarification": "Kept for a future checklist.",
                "stage": "post_eligibility_checklist",
            },
        ],
    }
    write_pathway(pathways_root, "fixture_stage", clarifications=clarifications)

    audit = audit_mod.audit_pathway("fixture_stage")

    messages = _rule_messages(audit, "dead_requirement_code")
    assert any("preserved_for_later" in m and "intentional" in m for m in messages)


def test_needs_manual_review_fallback_not_flagged_as_dead(pathways_root):
    clarifications = json.loads(json.dumps(DEFAULT_CLARIFICATIONS))
    clarifications["clarifications"].append(
        {
            "requirement": "needs_manual_review",
            "title": "Manual Review Required",
            "clarification": "Generic fallback.",
        }
    )
    write_pathway(pathways_root, "fixture_manual_review", clarifications=clarifications)

    audit = audit_mod.audit_pathway("fixture_manual_review")

    assert not any(
        "needs_manual_review" in m for m in _rule_messages(audit, "dead_requirement_code")
    )


# ---------------------------------------------------------------------------
# 6. acknowledgement-based hard failure severity warning
# ---------------------------------------------------------------------------


def test_acknowledgement_hard_failure_warning(pathways_root):
    rules_source = '''
HARD_FAILURES = {"income_below_minimum", "renewal_process_acknowledgement_missing"}


def _get_dotted(payload, key, default=None):
    current = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def evaluate_eligibility(payload):
    failed = []
    _get_dotted(payload, "routing.work_relationship")
    income = _get_dotted(payload, "financial.monthly_income_eur")
    if income is None:
        failed.append("income_below_minimum")
    ack = _get_dotted(payload, "compliance.renewal_process_acknowledged")
    if ack != "yes":
        failed.append("renewal_process_acknowledgement_missing")
    status = "not_eligible" if any(r in HARD_FAILURES for r in failed) else (
        "needs_review" if failed else "eligible"
    )
    return {"eligibility_status": status, "failed_requirements": failed, "pathway": "fixture"}
'''
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
        {
            "key": "compliance.renewal_process_acknowledged",
            "depends_on": ["financial.monthly_income_eur"],
            "label": "Do you acknowledge the renewal process?",
            "input_type": "choice",
            "required": True,
            "choices": ["yes", "no"],
        },
    ]
    write_pathway(pathways_root, "fixture_ack_hard_fail", fields=fields, rules_source=rules_source)

    audit = audit_mod.audit_pathway("fixture_ack_hard_fail")

    assert _has_finding(audit, "hard_failure_severity", "WARN")
    assert any(
        "renewal_process_acknowledgement_missing" in m
        for m in _rule_messages(audit, "hard_failure_severity")
    )
    # Severity is flagged, never auto-changed: the code must still be intact
    # in HARD_FAILURES as far as static extraction is concerned.
    assert "renewal_process_acknowledgement_missing" in audit_mod.RulesAnalysis(
        audit_mod.ast.parse(rules_source)
    ).hard_failures


# ---------------------------------------------------------------------------
# 7 & 8. invalid depends_on / applies_when
# ---------------------------------------------------------------------------


def test_invalid_depends_on_reference(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship", "routing.nonexistent_key"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
    ]
    write_pathway(pathways_root, "fixture_bad_depends_on", fields=fields)

    audit = audit_mod.audit_pathway("fixture_bad_depends_on")

    assert _has_finding(audit, "conditional_logic", "WARN")
    assert any("routing.nonexistent_key" in m for m in _rule_messages(audit, "conditional_logic"))
    # depends_on is documentation-only, so this must not be treated as a
    # structural FAIL.
    assert not any(
        f.rule == "conditional_logic" and f.severity == "FAIL" and "nonexistent_key" in f.message
        for f in audit.findings
    )


@pytest.mark.parametrize(
    "bad_condition",
    [
        {"unsupported_operator": ["routing.work_relationship", "employee"]},
        {"equals": "not-a-list"},
        {"equals": ["routing.work_relationship"]},  # wrong length
        {"equals": ["routing.does_not_exist", "employee"]},
    ],
)
def test_invalid_applies_when(pathways_root, bad_condition):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
            "applies_when": bad_condition,
        },
    ]
    write_pathway(pathways_root, "fixture_bad_applies_when", fields=fields)

    audit = audit_mod.audit_pathway("fixture_bad_applies_when")

    assert _has_finding(audit, "conditional_logic", "FAIL")
    assert audit.status == "FAIL"


def test_valid_applies_when_does_not_fail(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
            "applies_when": {"equals": ["routing.work_relationship", "employee"]},
        },
    ]
    write_pathway(pathways_root, "fixture_good_applies_when", fields=fields)

    audit = audit_mod.audit_pathway("fixture_good_applies_when")

    assert not _has_finding(audit, "conditional_logic", "FAIL")


def test_applies_when_referencing_impossible_choice_is_flagged(pathways_root):
    fields = [
        _default_field(choices=["employee", "contractor"]),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
            "applies_when": {"equals": ["routing.work_relationship", "business_owner"]},
        },
    ]
    write_pathway(pathways_root, "fixture_impossible_value", fields=fields)

    audit = audit_mod.audit_pathway("fixture_impossible_value")

    assert _has_finding(audit, "conditional_logic", "WARN")
    assert any("business_owner" in m for m in _rule_messages(audit, "conditional_logic"))


# ---------------------------------------------------------------------------
# 9. long / jargon question flagging
# ---------------------------------------------------------------------------


def test_long_label_flagging(pathways_root):
    long_label = "Is this a question " + ("that is very long " * 10) + "and should be flagged?"
    assert len(long_label) > audit_mod.LABEL_LENGTH_THRESHOLD
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": long_label,
            "input_type": "number",
            "required": True,
        },
    ]
    write_pathway(pathways_root, "fixture_long_label", fields=fields)

    audit = audit_mod.audit_pathway("fixture_long_label")

    assert _has_finding(audit, "question_length", "WARN")


def test_jargon_flagging(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
        {
            "key": "compliance.aima_step_acknowledged",
            "depends_on": ["financial.monthly_income_eur"],
            "label": "Do you understand the AIMA residence permit step?",
            "input_type": "choice",
            "required": True,
            "choices": ["yes", "no"],
        },
    ]
    write_pathway(pathways_root, "fixture_jargon", fields=fields)

    audit = audit_mod.audit_pathway("fixture_jargon")

    assert _has_finding(audit, "legal_jargon", "WARN")
    assert any("AIMA" in m for m in _rule_messages(audit, "legal_jargon"))


def test_jargon_word_boundary_does_not_false_positive(pathways_root):
    """'ARI' must not match inside ordinary words like 'arise'."""
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "Does this income arise from a qualifying source?",
            "input_type": "number",
            "required": True,
        },
    ]
    write_pathway(pathways_root, "fixture_no_false_jargon", fields=fields)

    audit = audit_mod.audit_pathway("fixture_no_false_jargon")

    assert not _has_finding(audit, "legal_jargon")


# ---------------------------------------------------------------------------
# 10. numeric band vs. numeric-rule flagging
# ---------------------------------------------------------------------------


def test_numeric_band_choice_flagged_when_rule_compares_numerically(pathways_root):
    rules_source = '''
MINIMUM_MONTHS = 6
HARD_FAILURES = {"months_below_minimum"}


def _get_dotted(payload, key, default=None):
    current = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def evaluate_eligibility(payload):
    failed = []
    _get_dotted(payload, "routing.work_relationship")
    # NOTE: the numeric-threshold heuristic matches this inline
    # get-then-compare style (the convention used consistently by every
    # real pathway's rules.py), not an assign-then-compare-later style --
    # see check_numeric_threshold_design's docstring/comment for why.
    if _as_int(_get_dotted(payload, "work.experience_months")) < MINIMUM_MONTHS:
        failed.append("months_below_minimum")
    status = "not_eligible" if failed else "eligible"
    return {"eligibility_status": status, "failed_requirements": failed, "pathway": "fixture"}
'''
    fields = [
        _default_field(),
        {
            "key": "work.experience_months",
            "depends_on": ["routing.work_relationship"],
            "label": "How much experience do you have?",
            "input_type": "choice",
            "required": True,
            "choices": ["less_than_6", "6_to_11", "12_or_more"],
        },
    ]
    write_pathway(pathways_root, "fixture_band_vs_numeric", fields=fields, rules_source=rules_source)

    audit = audit_mod.audit_pathway("fixture_band_vs_numeric")

    assert _has_finding(audit, "numeric_threshold_design", "WARN")
    assert any("work.experience_months" in m for m in _rule_messages(audit, "numeric_threshold_design"))


def test_numeric_input_type_not_flagged(pathways_root):
    rules_source = '''
MINIMUM_MONTHS = 6
HARD_FAILURES = {"months_below_minimum"}


def _get_dotted(payload, key, default=None):
    current = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def evaluate_eligibility(payload):
    failed = []
    _get_dotted(payload, "routing.work_relationship")
    months = _as_int(_get_dotted(payload, "work.experience_months"))
    if months is None or months < MINIMUM_MONTHS:
        failed.append("months_below_minimum")
    status = "not_eligible" if failed else "eligible"
    return {"eligibility_status": status, "failed_requirements": failed, "pathway": "fixture"}
'''
    fields = [
        _default_field(),
        {
            "key": "work.experience_months",
            "depends_on": ["routing.work_relationship"],
            "label": "How many months of experience do you have?",
            "input_type": "number",
            "required": True,
        },
    ]
    write_pathway(pathways_root, "fixture_numeric_ok", fields=fields, rules_source=rules_source)

    audit = audit_mod.audit_pathway("fixture_numeric_ok")

    assert not _has_finding(audit, "numeric_threshold_design")


# ---------------------------------------------------------------------------
# Redundancy: mirrored branch fields vs. genuine near-duplicates
# ---------------------------------------------------------------------------


def test_mirrored_branch_fields_are_not_flagged_as_redundant(pathways_root):
    """role.employee.monthly_income_eur vs role.contractor.monthly_income_eur
    is intentional per-branch conditional design (the same pattern used by
    every real QIQ pathway), not redundancy."""
    fields = [
        _default_field(),
        {
            "key": "role.employee.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your gross monthly salary in EUR before tax?",
            "input_type": "number",
            "required": True,
            "applies_when": {"equals": ["routing.work_relationship", "employee"]},
        },
        {
            "key": "role.contractor.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your gross monthly freelance income in EUR before tax?",
            "input_type": "number",
            "required": True,
            "applies_when": {"equals": ["routing.work_relationship", "contractor"]},
        },
    ]
    write_pathway(pathways_root, "fixture_mirrored_branch", fields=fields)

    audit = audit_mod.audit_pathway("fixture_mirrored_branch")

    assert not _has_finding(audit, "redundancy")


def test_genuine_near_duplicate_questions_are_flagged(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "role.pensionado.retired_from_habitual_occupation",
            "depends_on": ["routing.work_relationship"],
            "label": "Are you retired from your habitual occupation?",
            "input_type": "choice",
            "required": True,
            "choices": ["yes", "no"],
        },
        {
            "key": "role.pensionado.pension_retirement_based",
            "depends_on": ["role.pensionado.retired_from_habitual_occupation"],
            "label": "Does this income arise from your retirement or habitual occupation?",
            "input_type": "choice",
            "required": True,
            "choices": ["yes", "no"],
        },
    ]
    write_pathway(pathways_root, "fixture_genuine_duplicate", fields=fields)

    audit = audit_mod.audit_pathway("fixture_genuine_duplicate")

    assert _has_finding(audit, "redundancy", "WARN")


# ---------------------------------------------------------------------------
# 11. clean pathway passes
# ---------------------------------------------------------------------------


def test_clean_pathway_passes(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
    ]
    write_pathway(pathways_root, "fixture_clean", fields=fields)

    audit = audit_mod.audit_pathway("fixture_clean")

    assert audit.fails() == []
    assert audit.status in ("PASS", "PASS WITH WARNINGS")
    assert audit.scores["overall"] >= 8.0


def test_completely_clean_pathway_has_no_warnings_either(pathways_root):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
    ]
    write_pathway(pathways_root, "fixture_totally_clean", fields=fields, write_requirements_reference=True)

    audit = audit_mod.audit_pathway("fixture_totally_clean")

    assert audit.status == "PASS"
    assert audit.findings == []
    assert audit.scores == {
        "structural_correctness": 10.0,
        "ux_alignment": 10.0,
        "eligibility_flow_discipline": 10.0,
        "overall": 10.0,
    }


# ---------------------------------------------------------------------------
# 12 & 13. CLI exit-code behavior (strict vs. normal mode)
# ---------------------------------------------------------------------------


def test_normal_mode_exit_zero_on_warnings_only(pathways_root, capsys):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
        {
            "key": "routing.never_referenced_field",
            "depends_on": ["financial.monthly_income_eur"],
            "label": "This question is never read by rules.py.",
            "input_type": "choice",
            "required": True,
            "choices": ["yes", "no"],
        },
    ]
    write_pathway(pathways_root, "fixture_warn_only", fields=fields)

    exit_code = audit_mod.main(["--pathway", "fixture_warn_only", "--no-reports"])
    capsys.readouterr()

    assert exit_code == 0


def test_strict_mode_exit_nonzero_on_warnings(pathways_root, capsys):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
        {
            "key": "routing.never_referenced_field",
            "depends_on": ["financial.monthly_income_eur"],
            "label": "This question is never read by rules.py.",
            "input_type": "choice",
            "required": True,
            "choices": ["yes", "no"],
        },
    ]
    write_pathway(pathways_root, "fixture_warn_strict", fields=fields)

    exit_code = audit_mod.main(["--pathway", "fixture_warn_strict", "--strict", "--no-reports"])
    capsys.readouterr()

    assert exit_code == 1


def test_normal_and_strict_mode_exit_nonzero_on_failure(pathways_root, capsys):
    write_pathway(
        pathways_root,
        "fixture_fail_case",
        fields=[_default_field(choices=["yes", "no", "not_sure"])],
    )

    normal_exit = audit_mod.main(["--pathway", "fixture_fail_case", "--no-reports"])
    capsys.readouterr()
    strict_exit = audit_mod.main(["--pathway", "fixture_fail_case", "--strict", "--no-reports"])
    capsys.readouterr()

    assert normal_exit == 1
    assert strict_exit == 1


def test_clean_pathway_exits_zero_even_in_strict_mode(pathways_root, capsys):
    fields = [
        _default_field(),
        {
            "key": "financial.monthly_income_eur",
            "depends_on": ["routing.work_relationship"],
            "label": "What is your monthly income in EUR?",
            "input_type": "number",
            "required": True,
        },
    ]
    write_pathway(pathways_root, "fixture_clean_strict", fields=fields, write_requirements_reference=True)

    exit_code = audit_mod.main(["--pathway", "fixture_clean_strict", "--strict", "--no-reports"])
    capsys.readouterr()

    assert exit_code == 0


def test_json_output_mode(pathways_root, capsys):
    write_pathway(pathways_root, "fixture_json")

    exit_code = audit_mod.main(["--pathway", "fixture_json", "--json", "--no-reports"])
    out = capsys.readouterr().out

    assert exit_code == 0
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["pathway"] == "fixture_json"
    assert "scores" in data[0]
    assert "findings" in data[0]


def test_unknown_pathway_returns_error_exit_code(pathways_root, capsys):
    exit_code = audit_mod.main(["--pathway", "does_not_exist", "--no-reports"])
    capsys.readouterr()

    assert exit_code == 2


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_malformed_schema_fails(pathways_root):
    pathway_dir = pathways_root / "fixture_malformed"
    pathway_dir.mkdir()
    (pathway_dir / "questions.json").write_text(json.dumps({"pathway": "fixture_malformed"}), encoding="utf-8")
    (pathway_dir / "rules.py").write_text(DEFAULT_RULES_SOURCE, encoding="utf-8")

    audit = audit_mod.audit_pathway("fixture_malformed")

    assert audit.status == "FAIL"
    assert _has_finding(audit, "schema", "FAIL")


def test_invalid_json_reported_as_failure_not_crash(pathways_root):
    pathway_dir = pathways_root / "fixture_bad_json"
    pathway_dir.mkdir()
    (pathway_dir / "questions.json").write_text("{ not valid json", encoding="utf-8")
    (pathway_dir / "rules.py").write_text(DEFAULT_RULES_SOURCE, encoding="utf-8")

    audit = audit_mod.audit_pathway("fixture_bad_json")

    assert audit.status == "FAIL"
    assert _has_finding(audit, "schema", "FAIL")


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def test_reports_are_written_for_each_pathway_and_summary(pathways_root, tmp_path, capsys):
    write_pathway(pathways_root, "fixture_report_a")
    write_pathway(
        pathways_root,
        "fixture_report_b",
        fields=[_default_field(choices=["yes", "no", "not_sure"])],
    )

    audits = [audit_mod.audit_pathway("fixture_report_a"), audit_mod.audit_pathway("fixture_report_b")]
    audit_mod.write_reports(audits)

    report_dir = audit_mod.REPORT_DIR
    assert (report_dir / "fixture_report_a.md").exists()
    assert (report_dir / "fixture_report_b.md").exists()
    assert (report_dir / "summary.md").exists()

    summary_text = (report_dir / "summary.md").read_text(encoding="utf-8")
    assert "fixture_report_a" in summary_text
    assert "fixture_report_b" in summary_text

    pathway_a_text = (report_dir / "fixture_report_a.md").read_text(encoding="utf-8")
    for heading in (
        "## 1. Summary",
        "## 2. Errors",
        "## 3. Warnings",
        "## 4. Question-by-Question Findings",
        "## 5. Rule-Layer Findings",
        "## 6. Dead Code Findings",
        "## 7. Flow Metrics",
        "## 8. Costa Rica DNV Alignment",
        "## 9. Recommended Manual-Review Items",
    ):
        assert heading in pathway_a_text


def test_read_only_with_respect_to_pathway_source_files(pathways_root):
    """The audit must never modify questions.json/rules.py/etc. it reads."""
    pathway_dir = write_pathway(pathways_root, "fixture_readonly")
    before = {
        p.name: p.read_bytes()
        for p in pathway_dir.iterdir()
        if p.is_file()
    }

    audit_mod.audit_pathway("fixture_readonly")

    after = {
        p.name: p.read_bytes()
        for p in pathway_dir.iterdir()
        if p.is_file()
    }
    assert before == after


# ---------------------------------------------------------------------------
# Integration test against the real repository
# ---------------------------------------------------------------------------


def test_integration_audits_all_real_file_based_pathways():
    """Runs the audit tool against the actual repo. This intentionally does
    NOT require every pathway to PASS -- some pathways are expected to
    produce warnings/failures until cleaned up. It only asserts that the
    tool runs successfully and produces a result for every currently
    discoverable file-based pathway."""
    expected_pathways = {
        "costa_rica_pensionado",
        "italy_dnv",
        "italy_elective_residence",
        "portugal_d7",
        "portugal_dnv",
        "portugal_golden_visa",
        "spain_dnv",
        "spain_nlv",
        "spain_student_visa",
    }

    discovered = set(audit_mod.discover_pathways())
    assert expected_pathways.issubset(discovered)
    assert "costa_rica_dnv" not in discovered  # hardcoded benchmark, not file-based

    audits = audit_mod.run_audit()
    audited_names = {a.pathway for a in audits}
    assert expected_pathways.issubset(audited_names)

    for audit in audits:
        assert audit.status in ("PASS", "PASS WITH WARNINGS", "FAIL")
        assert set(audit.scores.keys()) == {
            "structural_correctness",
            "ux_alignment",
            "eligibility_flow_discipline",
            "overall",
        }
        for score in audit.scores.values():
            assert 0.0 <= score <= 10.0
        # The tool must not have crashed while auditing any real pathway.
        assert not _has_finding(audit, "audit_crash")

    # The tool reports current defects rather than hiding them: at least one
    # finding should exist somewhere across the real pathway set today.
    assert any(a.findings for a in audits)
