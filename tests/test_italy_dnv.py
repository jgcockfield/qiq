"""Tests for the Italy DNV question-flow cleanup.

Covers:
- exact question order for the self-employed and remote-worker routes
- relocated acknowledgement questions no longer appear in the eligibility flow
- their former hard-failure codes no longer produce not_eligible
- not_sure is retained only on the two approved questions
- all other hard-failure outcomes are unchanged
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from app.engine.evaluator import evaluate
from app.engine.pathways.italy_dnv.rules import evaluate_eligibility, HARD_FAILURES


QUESTIONS_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "engine"
    / "pathways"
    / "italy_dnv"
    / "questions.json"
)

RELOCATED_KEYS = {
    "role.digital_nomad.partita_iva_acknowledged",
    "compliance.permesso_8_day_acknowledged",
    "compliance.tax_social_security_acknowledged",
}


def _set_dotted(payload: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cur = payload
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def _walk_italy_dnv(answers: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    payload: Dict[str, Any] = {}
    asked_keys: List[str] = []

    for _ in range(40):
        result = evaluate(payload, pathway="italy_dnv")
        next_key = result.get("next_field_key")
        if next_key is None:
            return result, asked_keys

        asked_keys.append(next_key)
        assert next_key in answers, f"Missing test answer for {next_key}"
        _set_dotted(payload, next_key, answers[next_key])

    raise AssertionError("Italy DNV flow did not terminate within 40 steps")


SELF_EMPLOYED_ANSWERS = {
    "routing.worker_category": "self_employed_freelance",
    "identity.nationality": "United States",
    "identity.eu_citizen_status": "no",
    "work.remote_technological_tools_confirmed": "yes",
    "work.highly_qualified_basis": "have_a_relevant_degree",
    "work.prior_experience_months": "36",
    "financial.annual_work_income_eur": "30000",
    "financial.income_source_type": "remote_work_from_italy",
    "financial.income_evidence_types": ["tax_return", "bank_statements"],
    "role.digital_nomad.self_employment_proof_available": "yes",
    "routing.health_insurance_status": "have_it",
    "housing.accommodation_status": "have_qualifying_accommodation",
    "routing.passport_validity_months": "15",
    "routing.passport_blank_pages": "4",
    "routing.family_reunification_intent": "no_one_else",
}

REMOTE_WORKER_ANSWERS = {
    "routing.worker_category": "employee_or_collaborator",
    "identity.nationality": "United States",
    "identity.eu_citizen_status": "no",
    "work.remote_technological_tools_confirmed": "yes",
    "work.highly_qualified_basis": "have_a_relevant_degree",
    "work.prior_experience_months": "36",
    "financial.annual_work_income_eur": "30000",
    "financial.income_source_type": "remote_work_from_italy",
    "financial.income_evidence_types": ["tax_return", "bank_statements"],
    "role.remote_worker.contract_available": "yes",
    "role.remote_worker.employer_clean_record_declaration_available": "yes",
    "routing.health_insurance_status": "have_it",
    "housing.accommodation_status": "have_qualifying_accommodation",
    "routing.passport_validity_months": "15",
    "routing.passport_blank_pages": "4",
    "routing.family_reunification_intent": "spouse_or_minor_children",
    "routing.family_documents_available": "yes",
}


def test_self_employed_route_exact_question_order():
    result, asked_keys = _walk_italy_dnv(SELF_EMPLOYED_ANSWERS)

    assert asked_keys == [
        "routing.worker_category",
        "identity.nationality",
        "identity.eu_citizen_status",
        "work.remote_technological_tools_confirmed",
        "work.highly_qualified_basis",
        "work.prior_experience_months",
        "financial.annual_work_income_eur",
        "financial.income_source_type",
        "financial.income_evidence_types",
        "role.digital_nomad.self_employment_proof_available",
        "routing.health_insurance_status",
        "housing.accommodation_status",
        "routing.passport_validity_months",
        "routing.passport_blank_pages",
        "routing.family_reunification_intent",
    ]
    assert not any(key.startswith("role.remote_worker.") for key in asked_keys)

    eligibility = evaluate_eligibility(_to_answers_payload(SELF_EMPLOYED_ANSWERS))
    assert eligibility["eligibility_status"] == "eligible"
    assert eligibility["failed_requirements"] == []


def test_remote_worker_route_exact_question_order():
    result, asked_keys = _walk_italy_dnv(REMOTE_WORKER_ANSWERS)

    assert asked_keys == [
        "routing.worker_category",
        "identity.nationality",
        "identity.eu_citizen_status",
        "work.remote_technological_tools_confirmed",
        "work.highly_qualified_basis",
        "work.prior_experience_months",
        "financial.annual_work_income_eur",
        "financial.income_source_type",
        "financial.income_evidence_types",
        "role.remote_worker.contract_available",
        "role.remote_worker.employer_clean_record_declaration_available",
        "routing.health_insurance_status",
        "housing.accommodation_status",
        "routing.passport_validity_months",
        "routing.passport_blank_pages",
        "routing.family_reunification_intent",
        "routing.family_documents_available",
    ]
    assert not any(key.startswith("role.digital_nomad.") for key in asked_keys)

    eligibility = evaluate_eligibility(_to_answers_payload(REMOTE_WORKER_ANSWERS))
    assert eligibility["eligibility_status"] == "eligible"
    assert eligibility["failed_requirements"] == []


def test_relocated_questions_never_appear_in_eligibility_flow():
    for answers in (SELF_EMPLOYED_ANSWERS, REMOTE_WORKER_ANSWERS):
        _, asked_keys = _walk_italy_dnv(answers)
        for relocated_key in RELOCATED_KEYS:
            assert relocated_key not in asked_keys


def test_relocated_questions_removed_from_questions_json():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    live_keys = {field["key"] for field in data["taxonomy_fields"]}
    for relocated_key in RELOCATED_KEYS:
        assert relocated_key not in live_keys

    # Content must be preserved, not deleted outright.
    checklist_keys = {
        field["key"] for field in data["post_eligibility_checklist"]["fields"]
    }
    assert checklist_keys == RELOCATED_KEYS


def test_relocated_hard_failure_codes_removed_from_hard_failures():
    assert "permesso_acknowledgement_missing" not in HARD_FAILURES
    assert "tax_social_security_acknowledgement_missing" not in HARD_FAILURES


def test_missing_relocated_acknowledgements_no_longer_blocks_eligibility():
    # These payloads contain no permesso/tax_social_security/partita_iva keys at
    # all (since they're no longer asked) and must still resolve to eligible.
    self_employed_eligibility = evaluate_eligibility(
        _to_answers_payload(SELF_EMPLOYED_ANSWERS)
    )
    remote_worker_eligibility = evaluate_eligibility(
        _to_answers_payload(REMOTE_WORKER_ANSWERS)
    )

    for eligibility in (self_employed_eligibility, remote_worker_eligibility):
        assert eligibility["eligibility_status"] == "eligible"
        assert "permesso_acknowledgement_missing" not in eligibility["failed_requirements"]
        assert (
            "tax_social_security_acknowledgement_missing"
            not in eligibility["failed_requirements"]
        )
        assert (
            "partita_iva_acknowledgement_needs_review"
            not in eligibility["failed_requirements"]
        )


def test_not_sure_retained_only_on_two_approved_questions():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    fields_with_not_sure = {
        field["key"]
        for field in data["taxonomy_fields"]
        if any("not_sure" in str(choice) for choice in field.get("choices", []))
    }
    assert fields_with_not_sure == {
        "identity.eu_citizen_status",
        "role.remote_worker.employer_clean_record_declaration_available",
    }


def test_worker_category_choices_have_no_not_sure_and_use_plain_values():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "routing.worker_category"
    )
    assert field["choices"] == ["self_employed_freelance", "employee_or_collaborator"]


def test_highly_qualified_basis_merges_not_sure_and_none():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "work.highly_qualified_basis"
    )
    assert field["choices"] == [
        "have_a_relevant_degree",
        "certified_in_a_regulated_profession",
        "5plus_years_professional_experience",
        "3plus_years_it_executive_or_specialist_experience",
        "none_of_these",
    ]


def test_highly_qualified_basis_none_of_these_is_still_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.highly_qualified_basis"] = "none_of_these"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "highly_qualified_basis_not_met" in eligibility["failed_requirements"]


def test_other_hard_failures_unchanged():
    expected_unchanged_hard_failures = {
        "adult_children_or_parents_family_route_not_supported",
        "accommodation_unavailable",
        "digital_nomad_self_employment_proof_unavailable",
        "eu_citizen_status",
        "health_insurance_unavailable",
        "highly_qualified_basis_not_met",
        "income_below_minimum",
        "passive_income_not_accepted",
        "passport_blank_pages_below_minimum",
        "passport_validity_below_minimum",
        "prior_experience_below_minimum",
        "remote_technological_work_not_confirmed",
        "remote_worker_contract_unavailable",
        "remote_worker_employer_clean_record_unavailable",
    }
    assert HARD_FAILURES == expected_unchanged_hard_failures


def test_passport_blank_pages_severity_unchanged_still_hard():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["routing.passport_blank_pages"] = "1"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "passport_blank_pages_below_minimum" in eligibility["failed_requirements"]


def test_eu_citizen_hard_failure_still_fires():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["identity.eu_citizen_status"] = "yes"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "eu_citizen_status" in eligibility["failed_requirements"]


def test_eu_citizen_not_sure_value_routes_to_needs_review_not_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["identity.eu_citizen_status"] = "not_sure_dual_national"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "eu_citizen_status_needs_review" in eligibility["failed_requirements"]
    assert "eu_citizen_status" not in eligibility["failed_requirements"]


def test_employer_clean_record_not_sure_routes_to_needs_review():
    answers = deepcopy(REMOTE_WORKER_ANSWERS)
    answers["role.remote_worker.employer_clean_record_declaration_available"] = "not_sure"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert (
        "remote_worker_employer_clean_record_needs_review"
        in eligibility["failed_requirements"]
    )
    assert (
        "remote_worker_employer_clean_record_unavailable"
        not in eligibility["failed_requirements"]
    )


def test_adult_children_or_parents_still_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["routing.family_reunification_intent"] = "adult_children_or_parents"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert (
        "adult_children_or_parents_family_route_not_supported"
        in eligibility["failed_requirements"]
    )


def test_income_below_minimum_still_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["financial.annual_work_income_eur"] = "10000"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "income_below_minimum" in eligibility["failed_requirements"]


def _to_answers_payload(flat_answers: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in flat_answers.items():
        _set_dotted(payload, key, value)
    return payload
