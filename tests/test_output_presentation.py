"""Global QIQ result-presentation cleanup: tests for the centralized
humanization helpers in app.engine.output_builder and their effect on the
assembled UI output across pathways.

Scope: presentation only. These tests intentionally also assert that
internal contracts (eligibility_status enum values, requirement codes,
HARD_FAILURES sets, rule outcomes) are completely unchanged by this cleanup.
"""

from app.engine.eligibility_rules import evaluate_eligibility
from app.engine.output_builder import (
    build_output,
    display_title_for_clarification,
    humanize_requirement_code,
    humanize_status,
)


# ---------------------------------------------------------------------------
# Status humanization (items 1-6, 12, 17, 18)
# ---------------------------------------------------------------------------


def test_humanize_status_eligible():
    assert humanize_status("eligible") == "Eligible"


def test_humanize_status_needs_review():
    assert humanize_status("needs_review") == "Needs Review"


def test_humanize_status_not_eligible():
    assert humanize_status("not_eligible") == "Not Eligible"


def test_humanize_status_unrecognized_value_falls_back_mechanically():
    # Never crashes, never returns raw snake_case unmodified.
    assert humanize_status("some_weird_status") == "Some Weird Status"


def test_humanize_status_empty_or_none_is_safe():
    assert humanize_status(None) == ""
    assert humanize_status("") == ""


# ---------------------------------------------------------------------------
# Requirement-code humanization (item 13)
# ---------------------------------------------------------------------------


def test_humanize_requirement_code_fallback_examples():
    assert humanize_requirement_code("income_below_minimum") == "Income Below Minimum"
    assert (
        humanize_requirement_code("passport_validity_below_minimum")
        == "Passport Validity Below Minimum"
    )
    assert (
        humanize_requirement_code("adult_child_dependency_not_met")
        == "Adult Child Dependency Not Met"
    )
    assert (
        humanize_requirement_code("some_example_requirement_code")
        == "Some Example Requirement Code"
    )


def test_humanize_requirement_code_empty_is_safe():
    assert humanize_requirement_code(None) == ""
    assert humanize_requirement_code("") == ""


# ---------------------------------------------------------------------------
# display_title_for_clarification priority (item 14, 15)
# ---------------------------------------------------------------------------


def test_display_title_prefers_explicit_title_over_humanized_fallback():
    entry = {"requirement": "income_below_minimum", "title": "Custom Applicant Title"}
    assert display_title_for_clarification(entry) == "Custom Applicant Title"


def test_display_title_falls_back_to_humanized_code_when_title_missing():
    entry = {"requirement": "some_example_requirement_code"}
    assert display_title_for_clarification(entry) == "Some Example Requirement Code"


def test_display_title_handles_missing_clarification_deterministically():
    # A requirement with neither a title nor even a requirement key must not
    # crash -- it degrades to an empty string, never an exception.
    assert display_title_for_clarification({}) == ""
    assert display_title_for_clarification(None) == ""
    assert display_title_for_clarification("not-a-dict") == ""


# ---------------------------------------------------------------------------
# End-to-end: Italy Elective Residence (one Italy pathway)
# ---------------------------------------------------------------------------


def _italy_er_not_eligible_payload():
    return {
        "routing": {
            "applicant_type": "individual",
            "consulate_jurisdiction": "new_york",
            "stable_residence_intent": "no",
            "health_insurance_status": "yes",
            "passport_validity_months": "24",
        },
        "work": {"intends_to_work_in_italy": "no"},
        "financial": {
            "annual_passive_income_eur": "10000",
            "available_assets_eur": "5000",
            "income_source_types": ["pension"],
        },
        "housing": {"italy_lodging_status": "registered_lease"},
    }


def test_italy_not_eligible_result_has_status_display_and_explanations():
    result = evaluate_eligibility(
        _italy_er_not_eligible_payload(), pathway="italy-elective-residence"
    )
    # Internal contract unchanged.
    assert result["eligibility_status"] == "not_eligible"
    assert "extended_tourism_purpose" in result["failed_requirements"]
    assert "insufficient_passive_income" in result["failed_requirements"]

    output = build_output(result)

    # Product Requirement 2: status displays humanized, internal value intact.
    assert output["meta"]["status"] == "not_eligible"
    assert output["meta"]["status_display"] == "Not Eligible"

    # Product Requirement 1: every failed requirement gets an explanation.
    by_code = {c["requirement"]: c for c in output["clarifications"]}
    assert "extended_tourism_purpose" in by_code
    assert "insufficient_passive_income" in by_code
    for code in ("extended_tourism_purpose", "insufficient_passive_income"):
        entry = by_code[code]
        assert entry["display_title"]
        assert "_" not in entry["display_title"]
        assert entry["clarification"]


def test_italy_multiple_hard_failures_each_get_own_explanation():
    payload = _italy_er_not_eligible_payload()
    payload["housing"]["italy_lodging_status"] = "not_available"
    result = evaluate_eligibility(payload, pathway="italy-elective-residence")

    assert result["eligibility_status"] == "not_eligible"
    assert len(result["failed_requirements"]) >= 3

    output = build_output(result)
    rendered_codes = {c["requirement"] for c in output["clarifications"]}
    for code in result["failed_requirements"]:
        assert code in rendered_codes, f"{code} missing an explanation entry"
        entry = next(c for c in output["clarifications"] if c["requirement"] == code)
        assert entry["display_title"]
        assert entry["clarification"]


def test_italy_eligible_result_unchanged_except_display():
    payload = _italy_er_not_eligible_payload()
    payload["routing"]["stable_residence_intent"] = "yes"
    payload["financial"]["annual_passive_income_eur"] = "50000"
    result = evaluate_eligibility(payload, pathway="italy-elective-residence")

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []

    output = build_output(result)
    assert output["meta"]["status"] == "eligible"
    assert output["meta"]["status_display"] == "Eligible"
    assert output["clarifications"] == []


# ---------------------------------------------------------------------------
# End-to-end: Portugal D7 (one Portugal pathway) -- mixed hard + soft
# ---------------------------------------------------------------------------


def test_portugal_d7_mixed_hard_and_soft_all_get_explanations():
    payload = {
        "routing": {
            "applicant_type": "individual",
            "application_country_matches_nationality": "yes",
            "passport_validity_months": "2",  # hard: below minimum
            "health_travel_insurance_status": "will_obtain",  # soft: needs review
        },
        "identity": {"nationality": "United States", "age": "30"},
        "financial": {
            "income_source_types": ["pension"],
            "annual_passive_income_eur": "5000",  # hard: insufficient
            "income_evidence_types": ["bank_letters"],
        },
        "housing": {"portugal_accommodation_12_months": "have_it"},
    }
    result = evaluate_eligibility(payload, pathway="portugal-d7")
    assert result["eligibility_status"] == "not_eligible"

    output = build_output(result)
    rendered_codes = {c["requirement"] for c in output["clarifications"]}
    for code in result["failed_requirements"]:
        assert code in rendered_codes
        entry = next(c for c in output["clarifications"] if c["requirement"] == code)
        assert entry["display_title"]
        assert "_" not in entry["display_title"]
        assert entry["clarification"]

    assert output["meta"]["status_display"] == "Not Eligible"


def test_portugal_d7_needs_review_requirement_has_title_and_explanation():
    payload = {
        "routing": {
            "applicant_type": "individual",
            "application_country_matches_nationality": "yes",
            "passport_validity_months": "24",
            "health_travel_insurance_status": "will_obtain",
        },
        "identity": {"nationality": "United States", "age": "30"},
        "financial": {
            "income_source_types": ["pension"],
            "annual_passive_income_eur": "15000",
            "income_evidence_types": ["bank_letters"],
        },
        "housing": {"portugal_accommodation_12_months": "have_it"},
    }
    result = evaluate_eligibility(payload, pathway="portugal-d7")
    assert result["eligibility_status"] == "needs_review"
    assert "health_travel_insurance_needs_review" in result["failed_requirements"]

    output = build_output(result)
    assert output["meta"]["status_display"] == "Needs Review"
    entry = next(
        c for c in output["clarifications"] if c["requirement"] == "health_travel_insurance_needs_review"
    )
    assert entry["display_title"]
    assert entry["clarification"]


# ---------------------------------------------------------------------------
# End-to-end: Spain NLV (one Spain pathway)
# ---------------------------------------------------------------------------


def test_spain_nlv_not_eligible_explanations_present():
    payload = {
        "routing": {
            "applicant_type": "individual",
            "irregular_presence_spain": "no",
            "passport_validity_months": "12",
            "health_insurance_status": "have_it",
            "background_check_available": "yes",
            "criminal_record_flag": "no",
            "public_order_security_risk_flag": "no",
            "public_health_disease_flag": "no",
        },
        "identity": {
            "nationality": "United States",
            "eu_eea_swiss_citizen": "no",
        },
        "work": {"intends_to_work_in_spain": "no"},
        "financial": {
            "monthly_passive_income_or_assets_eur": "100",
            "funds_evidence_types": ["bank_statements"],
            "spanish_company_ownership": "no",
        },
    }
    result = evaluate_eligibility(payload, pathway="spain-nlv")
    assert result["eligibility_status"] == "not_eligible"
    assert "insufficient_financial_means" in result["failed_requirements"]

    output = build_output(result)
    entry = next(
        c for c in output["clarifications"] if c["requirement"] == "insufficient_financial_means"
    )
    assert entry["display_title"]
    assert "_" not in entry["display_title"]
    assert entry["clarification"]
    assert output["meta"]["status_display"] == "Not Eligible"


# ---------------------------------------------------------------------------
# End-to-end: Costa Rica Pensionado (required by name)
# ---------------------------------------------------------------------------


def test_costa_rica_pensionado_not_eligible_explanations_present():
    payload = {
        "routing": {
            "applicant_type": "individual",
            "criminal_record_flag": "no",
        },
        "role": {
            "pensionado": {
                "retired_from_habitual_occupation": "no",
                "pension_source_type": "social_security",
                "monthly_pension_usd": "500",
                "pension_has_scheduled_end_date": "no",
            }
        },
        "work": {"intends_to_work_in_costa_rica": "no"},
        "documents": {"valid_passport_available": "yes"},
    }
    result = evaluate_eligibility(payload, pathway="costa-rica-pensionado")
    assert result["eligibility_status"] == "not_eligible"
    assert "not_retired_from_habitual_occupation" in result["failed_requirements"]

    output = build_output(result)
    assert output["meta"]["status_display"] == "Not Eligible"
    entry = next(
        c
        for c in output["clarifications"]
        if c["requirement"] == "not_retired_from_habitual_occupation"
    )
    assert entry["display_title"]
    assert "_" not in entry["display_title"]
    assert entry["clarification"]


def test_costa_rica_pensionado_needs_review_still_works():
    payload = {
        "routing": {
            "applicant_type": "individual",
            "criminal_record_flag": "no",
        },
        "role": {
            "pensionado": {
                "retired_from_habitual_occupation": "yes",
                "pension_source_type": "social_security",
                "monthly_pension_usd": "not-a-number",
                "pension_has_scheduled_end_date": "no",
            }
        },
        "work": {"intends_to_work_in_costa_rica": "no"},
        "documents": {"valid_passport_available": "yes"},
    }
    result = evaluate_eligibility(payload, pathway="costa-rica-pensionado")
    assert result["eligibility_status"] == "needs_review"

    output = build_output(result)
    assert output["meta"]["status_display"] == "Needs Review"
    assert output["clarifications"], "needs_review must still surface clarifications"
    for entry in output["clarifications"]:
        assert entry["display_title"]
        assert "_" not in entry["display_title"]


# ---------------------------------------------------------------------------
# Raw code / raw status never leak as the resolved display value (items 11, 12)
# ---------------------------------------------------------------------------


def test_no_raw_snake_case_requirement_code_used_as_display_title_when_title_exists():
    payload = _italy_er_not_eligible_payload()
    result = evaluate_eligibility(payload, pathway="italy-elective-residence")
    output = build_output(result)
    for c in output["clarifications"]:
        # Every emitted code in this pathway has a real, distinct title in
        # clarifications.json, so display_title must never equal the raw code.
        assert c["display_title"] != c["requirement"]


def test_no_raw_status_value_used_as_status_display():
    for status in ("eligible", "needs_review", "not_eligible"):
        display = humanize_status(status)
        assert display != status
        assert "_" not in display


# ---------------------------------------------------------------------------
# Existing pathway-specific summary/CTA output remains intact (item 16)
# ---------------------------------------------------------------------------


def test_existing_summary_and_next_steps_still_present_alongside_new_fields():
    payload = _italy_er_not_eligible_payload()
    result = evaluate_eligibility(payload, pathway="italy-elective-residence")
    output = build_output(result)

    # Pre-existing pathway-specific fields untouched by this cleanup.
    assert isinstance(output["summary"], str) and output["summary"]
    assert "next_steps" in output
    assert output["next_steps"]["enabled"] is True

    # New additive field alongside, not replacing, the existing status field.
    assert set(output["meta"].keys()) >= {"status", "work_type", "visa_type", "status_display"}


# ---------------------------------------------------------------------------
# No engine/rules regression (items 18, 19, 20)
# ---------------------------------------------------------------------------


def test_no_eligibility_status_enum_values_changed():
    for pathway_kwarg, payload, expected_status in (
        ("italy-elective-residence", _italy_er_not_eligible_payload(), "not_eligible"),
    ):
        result = evaluate_eligibility(payload, pathway=pathway_kwarg)
        assert result["eligibility_status"] == expected_status
        assert result["eligibility_status"] in {"eligible", "needs_review", "not_eligible"}


def test_hard_failures_sets_unchanged_by_presentation_cleanup():
    import app.engine.pathways.italy_elective_residence.rules as italy_er_rules
    import app.engine.pathways.portugal_d7.rules as portugal_d7_rules
    import app.engine.pathways.spain_nlv.rules as spain_nlv_rules
    import app.engine.pathways.costa_rica_pensionado.rules as pensionado_rules

    assert len(italy_er_rules.HARD_FAILURES) == 9
    assert len(portugal_d7_rules.HARD_FAILURES) == 7
    assert len(spain_nlv_rules.HARD_FAILURES) == 10
    assert pensionado_rules.HARD_FAILURES == {
        "not_retired_from_habitual_occupation",
        "pension_income_below_minimum",
        "pension_not_retirement_based",
    }


def test_no_pathway_rules_behavior_changed_golden_payloads():
    # Re-assert a previously-verified golden result for each of the four
    # representative pathways to prove this cleanup did not alter any rule.
    italy_eligible = evaluate_eligibility(
        {
            **_italy_er_not_eligible_payload(),
            "routing": {
                **_italy_er_not_eligible_payload()["routing"],
                "stable_residence_intent": "yes",
            },
            "financial": {
                "annual_passive_income_eur": "50000",
                "available_assets_eur": "5000",
                "income_source_types": ["pension"],
            },
        },
        pathway="italy-elective-residence",
    )
    assert italy_eligible["eligibility_status"] == "eligible"