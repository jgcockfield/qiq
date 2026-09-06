"""Tests for the Italy DNV targeted cleanup (rounds 2 and 3).

Round 2 covers:
- exact question order for the self-employed and remote-worker routes
  (shorter: income-source split into a yes/no gate + conditional follow-up)
- relocated acknowledgement questions still don't appear in the eligibility flow
- their former hard-failure codes still don't make applicants not_eligible
- zero not_sure choices remain anywhere in the live flow (both previously
  "retained" exceptions are gone)
- work.highly_qualified_basis uses plain-English choice tokens
- "w2" removed from income evidence choices
- financial.income_from_remote_work_confirmed / non_remote_income_source
  replace the old "always needs review" peer-choice design
- passport_blank_pages_below_minimum is now needs_review, not hard
- all still-applicable hard-failure outcomes are unchanged

Round 3 covers a regression fix: round 2 folded the remote-work confirmation
into routing.worker_category's description only, losing a distinct
eligibility question/hard-failure. work.remote_work_confirmed restores it
with simpler wording (no "technological tools" phrasing), positioned right
after routing.worker_category, with no not_sure/escape choice.
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


def _to_answers_payload(flat_answers: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in flat_answers.items():
        _set_dotted(payload, key, value)
    return payload


SELF_EMPLOYED_ANSWERS = {
    "routing.worker_category": "self_employed_freelance",
    "work.remote_work_confirmed": "yes",
    "identity.nationality": "United States",
    "identity.eu_citizen_status": "no",
    "work.highly_qualified_basis": "university_degree",
    "work.prior_experience_months": "36",
    "financial.annual_work_income_eur": "30000",
    "financial.income_from_remote_work_confirmed": "yes",
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
    "work.remote_work_confirmed": "yes",
    "identity.nationality": "United States",
    "identity.eu_citizen_status": "no",
    "work.highly_qualified_basis": "university_degree",
    "work.prior_experience_months": "36",
    "financial.annual_work_income_eur": "30000",
    "financial.income_from_remote_work_confirmed": "yes",
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
        "work.remote_work_confirmed",
        "identity.nationality",
        "identity.eu_citizen_status",
        "work.highly_qualified_basis",
        "work.prior_experience_months",
        "financial.annual_work_income_eur",
        "financial.income_from_remote_work_confirmed",
        "financial.income_evidence_types",
        "role.digital_nomad.self_employment_proof_available",
        "routing.health_insurance_status",
        "housing.accommodation_status",
        "routing.passport_validity_months",
        "routing.passport_blank_pages",
        "routing.family_reunification_intent",
    ]
    assert "work.remote_technological_tools_confirmed" not in asked_keys
    assert "financial.non_remote_income_source" not in asked_keys  # skipped, answered "yes"
    assert not any(key.startswith("role.remote_worker.") for key in asked_keys)

    eligibility = evaluate_eligibility(_to_answers_payload(SELF_EMPLOYED_ANSWERS))
    assert eligibility["eligibility_status"] == "eligible"
    assert eligibility["failed_requirements"] == []


def test_remote_worker_route_exact_question_order():
    result, asked_keys = _walk_italy_dnv(REMOTE_WORKER_ANSWERS)

    assert asked_keys == [
        "routing.worker_category",
        "work.remote_work_confirmed",
        "identity.nationality",
        "identity.eu_citizen_status",
        "work.highly_qualified_basis",
        "work.prior_experience_months",
        "financial.annual_work_income_eur",
        "financial.income_from_remote_work_confirmed",
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
    assert "work.remote_technological_tools_confirmed" not in asked_keys
    assert not any(key.startswith("role.digital_nomad.") for key in asked_keys)

    eligibility = evaluate_eligibility(_to_answers_payload(REMOTE_WORKER_ANSWERS))
    assert eligibility["eligibility_status"] == "eligible"
    assert eligibility["failed_requirements"] == []


def test_non_remote_income_source_question_appears_only_when_answer_is_no():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["financial.income_from_remote_work_confirmed"] = "no"
    answers["financial.non_remote_income_source"] = "other_active_work"

    _, asked_keys = _walk_italy_dnv(answers)
    assert "financial.non_remote_income_source" in asked_keys
    # It must come right after the yes/no gate.
    gate_index = asked_keys.index("financial.income_from_remote_work_confirmed")
    assert asked_keys[gate_index + 1] == "financial.non_remote_income_source"


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

    checklist_keys = {
        field["key"] for field in data["post_eligibility_checklist"]["fields"]
    }
    assert checklist_keys == RELOCATED_KEYS


def test_relocated_hard_failure_codes_removed_from_hard_failures():
    assert "permesso_acknowledgement_missing" not in HARD_FAILURES
    assert "tax_social_security_acknowledgement_missing" not in HARD_FAILURES


def test_missing_relocated_acknowledgements_no_longer_blocks_eligibility():
    for answers in (SELF_EMPLOYED_ANSWERS, REMOTE_WORKER_ANSWERS):
        eligibility = evaluate_eligibility(_to_answers_payload(answers))
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


def test_no_not_sure_choices_remain_anywhere_in_the_live_flow():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    fields_with_not_sure = {
        field["key"]
        for field in data["taxonomy_fields"]
        if any("not_sure" in str(choice) for choice in field.get("choices", []))
    }
    assert fields_with_not_sure == set()


def test_old_remote_technological_tools_key_stays_removed():
    # The old key/wording ("using a computer or other technological tools")
    # must not come back — only the new, simpler work.remote_work_confirmed.
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    live_keys = {field["key"] for field in data["taxonomy_fields"]}
    assert "work.remote_technological_tools_confirmed" not in live_keys

    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "work.remote_work_confirmed"
    )
    assert "technological tools" not in field["label"].lower()
    assert "computer" not in field["label"].lower()


def test_remote_work_confirmed_question_shape_and_position():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    keys_in_order = [f["key"] for f in data["taxonomy_fields"]]
    assert keys_in_order.index("work.remote_work_confirmed") == (
        keys_in_order.index("routing.worker_category") + 1
    )

    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "work.remote_work_confirmed"
    )
    assert field["label"] == "Will you be working remotely while living in Italy?"
    assert field["input_type"] == "choice"
    assert field["choices"] == ["yes", "no"]
    assert field["required"] is True


def test_remote_work_confirmed_no_escape_choice():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "work.remote_work_confirmed"
    )
    assert not any("not_sure" in str(choice) for choice in field["choices"])
    assert not any("not_ready" in str(choice) for choice in field["choices"])
    assert not any("unknown" in str(choice) for choice in field["choices"])


def test_remote_work_confirmed_yes_continues_to_eligible():
    # SELF_EMPLOYED_ANSWERS/REMOTE_WORKER_ANSWERS both answer "yes" already;
    # confirmed eligible in the exact-question-order tests above. This test
    # isolates just the remote-work criterion's contribution.
    eligibility = evaluate_eligibility(_to_answers_payload(SELF_EMPLOYED_ANSWERS))
    assert "remote_technological_work_not_confirmed" not in eligibility["failed_requirements"]
    assert "remote_technological_work_needs_review" not in eligibility["failed_requirements"]


def test_remote_work_confirmed_no_produces_not_eligible():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.remote_work_confirmed"] = "no"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "remote_technological_work_not_confirmed" in eligibility["failed_requirements"]


def test_remote_work_confirmed_malformed_value_defensively_routes_to_needs_review():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.remote_work_confirmed"] = ""
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "remote_technological_work_needs_review" in eligibility["failed_requirements"]
    assert "remote_technological_work_not_confirmed" not in eligibility["failed_requirements"]


def test_worker_category_choices_unchanged():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "routing.worker_category"
    )
    assert field["choices"] == ["self_employed_freelance", "employee_or_collaborator"]


def test_highly_qualified_basis_uses_plain_choices():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "work.highly_qualified_basis"
    )
    assert field["choices"] == [
        "university_degree",
        "licensed_professional",
        "at_least_5_years_experience",
        "at_least_3_years_senior_tech_experience",
        "none_of_these",
    ]
    # No leading-digit tokens like "5plus_..." that display oddly.
    assert not any(choice.startswith(("5plus", "3plus")) for choice in field["choices"])


def test_highly_qualified_basis_none_of_these_is_still_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.highly_qualified_basis"] = "none_of_these"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "highly_qualified_basis_not_met" in eligibility["failed_requirements"]


def test_income_evidence_types_has_no_w2_choice():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "financial.income_evidence_types"
    )
    assert "w2" not in field["choices"]


def test_income_from_remote_work_yes_produces_no_failure():
    eligibility = evaluate_eligibility(_to_answers_payload(SELF_EMPLOYED_ANSWERS))
    assert "income_source_needs_review" not in eligibility["failed_requirements"]
    assert "passive_income_not_accepted" not in eligibility["failed_requirements"]


def test_income_from_remote_work_no_with_passive_income_is_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["financial.income_from_remote_work_confirmed"] = "no"
    answers["financial.non_remote_income_source"] = "passive_income"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "passive_income_not_accepted" in eligibility["failed_requirements"]


def test_income_from_remote_work_no_with_other_active_work_is_soft_review():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["financial.income_from_remote_work_confirmed"] = "no"
    answers["financial.non_remote_income_source"] = "other_active_work"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "income_source_needs_review" in eligibility["failed_requirements"]
    assert "passive_income_not_accepted" not in eligibility["failed_requirements"]


def test_hard_failures_set_current_state():
    expected_hard_failures = {
        "adult_children_or_parents_family_route_not_supported",
        "accommodation_unavailable",
        "digital_nomad_self_employment_proof_unavailable",
        "eu_citizen_status",
        "health_insurance_unavailable",
        "highly_qualified_basis_not_met",
        "income_below_minimum",
        "passive_income_not_accepted",
        "passport_validity_below_minimum",
        "prior_experience_below_minimum",
        "remote_technological_work_not_confirmed",
        "remote_worker_contract_unavailable",
        "remote_worker_employer_clean_record_unavailable",
    }
    assert HARD_FAILURES == expected_hard_failures
    # passport_blank_pages softening (previous round) is unaffected by this fix.
    assert "passport_blank_pages_below_minimum" not in HARD_FAILURES
    # remote-work criterion is restored as a hard failure by this fix.
    assert "remote_technological_work_not_confirmed" in HARD_FAILURES


def test_passport_blank_pages_below_minimum_is_now_needs_review_not_hard():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["routing.passport_blank_pages"] = "1"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "passport_blank_pages_below_minimum" in eligibility["failed_requirements"]


def test_eu_citizen_hard_failure_still_fires():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["identity.eu_citizen_status"] = "yes"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "eu_citizen_status" in eligibility["failed_requirements"]


def test_eu_citizen_malformed_value_defensively_routes_to_needs_review():
    # not_sure is no longer an offered choice, but rules.py should still
    # degrade gracefully (needs_review, not a crash or false pass) if an
    # unexpected value ever arrives.
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["identity.eu_citizen_status"] = ""
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "eu_citizen_status_needs_review" in eligibility["failed_requirements"]
    assert "eu_citizen_status" not in eligibility["failed_requirements"]


def test_employer_clean_record_malformed_value_defensively_routes_to_needs_review():
    answers = deepcopy(REMOTE_WORKER_ANSWERS)
    answers["role.remote_worker.employer_clean_record_declaration_available"] = ""
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


def test_employer_clean_record_choices_have_no_not_sure():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f
        for f in data["taxonomy_fields"]
        if f["key"] == "role.remote_worker.employer_clean_record_declaration_available"
    )
    assert field["choices"] == ["yes", "no"]
    assert "declaration" not in field["label"].lower()


def test_housing_wording_matches_its_choices():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    field = next(
        f for f in data["taxonomy_fields"] if f["key"] == "housing.accommodation_status"
    )
    assert field["label"] == "Do you have accommodation arranged in Italy for the visa period?"
    assert field["choices"] == [
        "have_qualifying_accommodation",
        "will_secure_before_travel",
        "not_available",
    ]


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
