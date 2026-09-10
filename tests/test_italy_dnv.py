"""Tests for the Italy DNV canonical-parity cleanup.

The live eligibility flow (questions.json + rules.py) now matches the
approved canonical Markdown (questions_dnv.md) exactly: 12 distinct fields,
2 of them conditional on the Employee / Collaborator route. This round:

- consolidated the income question (dropped the remote-work-source yes/no
  gate and its passive-income follow-up; the amount itself is now scoped to
  "income...from the remote work you will perform")
- removed identity.nationality (dead data, never evaluated)
- removed role.digital_nomad.self_employment_proof_available and its codes
  (self-employed status is represented by routing.worker_category itself;
  documentary proof belongs downstream)
- removed financial.income_evidence_types and its code (document checklist)
- simplified health insurance and accommodation from 3-way status fields to
  factual Yes/No questions (the "will_obtain" / "will_secure_before_travel"
  needs_review states are intentionally collapsed into "Yes")
- removed routing.passport_blank_pages and its codes (consulate-specific
  filing logistics, not initial eligibility)
- removed routing.family_documents_available and its code (the substantive
  family-category fact remains routing.family_reunification_intent)
- removed routing.additional_information (no eligibility effect)
- reworded several questions to match canonical wording exactly

Partita IVA, permesso di soggiorno, and tax/social-security acknowledgements
remain inert in post_eligibility_checklist, unaffected by this round.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from app.engine.evaluator import evaluate
from app.engine.pathways.italy_dnv.rules import evaluate_eligibility, HARD_FAILURES


BASE = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "engine"
    / "pathways"
    / "italy_dnv"
)
QUESTIONS_PATH = BASE / "questions.json"
QUESTIONS_DNV_PATH = BASE / "questions_dnv.md"
RULES_PATH = BASE / "rules.py"
CLARIFICATIONS_PATH = BASE / "clarifications.json"
OUTPUT_PATH = BASE / "output.json"

RELOCATED_KEYS = {
    "role.digital_nomad.partita_iva_acknowledged",
    "compliance.permesso_8_day_acknowledged",
    "compliance.tax_social_security_acknowledged",
}

REMOVED_LIVE_KEYS = {
    "identity.nationality",
    "role.digital_nomad.self_employment_proof_available",
    "financial.income_from_remote_work_confirmed",
    "financial.non_remote_income_source",
    "financial.income_evidence_types",
    "routing.passport_blank_pages",
    "routing.family_documents_available",
    "routing.additional_information",
}

REMOVED_CODES = {
    "digital_nomad_self_employment_proof_unavailable",
    "digital_nomad_self_employment_proof_needs_review",
    "income_source_needs_review",
    "passive_income_not_accepted",
    "income_evidence_needs_review",
    "passport_blank_pages_needs_review",
    "passport_blank_pages_below_minimum",
    "family_documents_needs_review",
}

EXPECTED_HARD_FAILURES = {
    "remote_technological_work_not_confirmed",
    "eu_citizen_status",
    "highly_qualified_basis_not_met",
    "prior_experience_below_minimum",
    "income_below_minimum",
    "remote_worker_contract_unavailable",
    "remote_worker_employer_clean_record_unavailable",
    "health_insurance_unavailable",
    "accommodation_unavailable",
    "passport_validity_below_minimum",
    "adult_children_or_parents_family_route_not_supported",
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


def _load_questions() -> Dict[str, Any]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def _fields_by_key() -> Dict[str, Any]:
    return {f["key"]: f for f in _load_questions()["taxonomy_fields"]}


SELF_EMPLOYED_ANSWERS = {
    "routing.worker_category": "self_employed_freelance",
    "work.remote_work_confirmed": "yes",
    "identity.eu_citizen_status": "no",
    "work.highly_qualified_basis": "university_degree",
    "work.prior_experience_months": "36",
    "financial.annual_work_income_eur": "30000",
    "routing.health_insurance_status": "yes",
    "housing.accommodation_status": "yes",
    "routing.passport_validity_months": "15",
    "routing.family_reunification_intent": "no_one_else",
}

REMOTE_WORKER_ANSWERS = {
    "routing.worker_category": "employee_or_collaborator",
    "work.remote_work_confirmed": "yes",
    "identity.eu_citizen_status": "no",
    "work.highly_qualified_basis": "university_degree",
    "work.prior_experience_months": "36",
    "financial.annual_work_income_eur": "30000",
    "role.remote_worker.contract_available": "yes",
    "role.remote_worker.employer_clean_record_declaration_available": "yes",
    "routing.health_insurance_status": "yes",
    "housing.accommodation_status": "yes",
    "routing.passport_validity_months": "15",
    "routing.family_reunification_intent": "spouse_or_minor_children",
}


# ---------------------------------------------------------------------------
# Canonical / runtime parity
# ---------------------------------------------------------------------------


def test_canonical_and_live_sequence_parity():
    md_text = QUESTIONS_DNV_PATH.read_text(encoding="utf-8")
    md_questions = []
    for line in (l.strip() for l in md_text.splitlines()):
        if not line or line.startswith("#") or line == "---" or line.startswith("- "):
            continue
        md_questions.append(line)

    data = _load_questions()
    live_labels = [f["label"] for f in data["taxonomy_fields"]]

    assert live_labels == md_questions
    assert len(live_labels) == 12


def test_self_employed_route_exact_question_order():
    result, asked_keys = _walk_italy_dnv(SELF_EMPLOYED_ANSWERS)

    assert asked_keys == [
        "routing.worker_category",
        "work.remote_work_confirmed",
        "identity.eu_citizen_status",
        "work.highly_qualified_basis",
        "work.prior_experience_months",
        "financial.annual_work_income_eur",
        "routing.health_insurance_status",
        "housing.accommodation_status",
        "routing.passport_validity_months",
        "routing.family_reunification_intent",
    ]
    assert len(asked_keys) == 10
    assert not any(key.startswith("role.") for key in asked_keys)

    eligibility = evaluate_eligibility(_to_answers_payload(SELF_EMPLOYED_ANSWERS))
    assert eligibility["eligibility_status"] == "eligible"
    assert eligibility["failed_requirements"] == []


def test_remote_worker_route_exact_question_order():
    result, asked_keys = _walk_italy_dnv(REMOTE_WORKER_ANSWERS)

    assert asked_keys == [
        "routing.worker_category",
        "work.remote_work_confirmed",
        "identity.eu_citizen_status",
        "work.highly_qualified_basis",
        "work.prior_experience_months",
        "financial.annual_work_income_eur",
        "role.remote_worker.contract_available",
        "role.remote_worker.employer_clean_record_declaration_available",
        "routing.health_insurance_status",
        "housing.accommodation_status",
        "routing.passport_validity_months",
        "routing.family_reunification_intent",
    ]
    assert len(asked_keys) == 12

    eligibility = evaluate_eligibility(_to_answers_payload(REMOTE_WORKER_ANSWERS))
    assert eligibility["eligibility_status"] == "eligible"
    assert eligibility["failed_requirements"] == []


# ---------------------------------------------------------------------------
# 1. Work type
# ---------------------------------------------------------------------------


def test_worker_category_first_and_two_internal_values():
    data = _load_questions()
    assert data["taxonomy_fields"][0]["key"] == "routing.worker_category"

    field = _fields_by_key()["routing.worker_category"]
    assert field["choices"] == ["self_employed_freelance", "employee_or_collaborator"]
    assert field["label"] == "How do you work?"


def test_worker_category_missing_is_needs_review():
    eligibility = evaluate_eligibility(_to_answers_payload({}))
    assert eligibility["eligibility_status"] in ("needs_review", "not_eligible")
    assert "worker_category_missing_or_unrecognized" in eligibility["failed_requirements"]
    assert "worker_category_missing_or_unrecognized" not in HARD_FAILURES


# ---------------------------------------------------------------------------
# 2. Remote work
# ---------------------------------------------------------------------------


def test_remote_work_confirmed_yes_passes():
    eligibility = evaluate_eligibility(_to_answers_payload(SELF_EMPLOYED_ANSWERS))
    assert "remote_technological_work_not_confirmed" not in eligibility["failed_requirements"]
    assert "remote_technological_work_needs_review" not in eligibility["failed_requirements"]


def test_remote_work_confirmed_no_is_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.remote_work_confirmed"] = "no"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "remote_technological_work_not_confirmed" in eligibility["failed_requirements"]


def test_remote_work_confirmed_missing_is_needs_review():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.remote_work_confirmed"] = ""
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "remote_technological_work_needs_review" in eligibility["failed_requirements"]
    assert "remote_technological_work_not_confirmed" not in eligibility["failed_requirements"]


# ---------------------------------------------------------------------------
# 3. Citizenship
# ---------------------------------------------------------------------------


def test_nationality_field_absent():
    live_keys = {f["key"] for f in _load_questions()["taxonomy_fields"]}
    assert "identity.nationality" not in live_keys

    source_text = RULES_PATH.read_text(encoding="utf-8")
    assert '"identity.nationality"' not in source_text


def test_eu_citizen_status_hard_failure_and_pass():
    yes_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    yes_answers["identity.eu_citizen_status"] = "yes"
    eligibility = evaluate_eligibility(_to_answers_payload(yes_answers))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert "eu_citizen_status" in eligibility["failed_requirements"]

    no_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    no_answers["identity.eu_citizen_status"] = "no"
    eligibility = evaluate_eligibility(_to_answers_payload(no_answers))
    assert "eu_citizen_status" not in eligibility["failed_requirements"]


def test_eu_citizen_status_missing_is_needs_review():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["identity.eu_citizen_status"] = ""
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "eu_citizen_status_needs_review" in eligibility["failed_requirements"]
    assert "eu_citizen_status" not in eligibility["failed_requirements"]


# ---------------------------------------------------------------------------
# 4. Qualification
# ---------------------------------------------------------------------------


def test_highly_qualified_basis_exact_five_values():
    field = _fields_by_key()["work.highly_qualified_basis"]
    assert field["choices"] == [
        "university_degree",
        "licensed_professional",
        "at_least_5_years_experience",
        "at_least_3_years_senior_tech_experience",
        "none_of_these",
    ]


def test_highly_qualified_basis_none_of_these_is_hard_failure():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.highly_qualified_basis"] = "none_of_these"
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "not_eligible"
    assert "highly_qualified_basis_not_met" in eligibility["failed_requirements"]


def test_highly_qualified_basis_missing_is_needs_review():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    answers["work.highly_qualified_basis"] = ""
    eligibility = evaluate_eligibility(_to_answers_payload(answers))

    assert eligibility["eligibility_status"] == "needs_review"
    assert "highly_qualified_basis_needs_review" in eligibility["failed_requirements"]


# ---------------------------------------------------------------------------
# 5. Prior experience
# ---------------------------------------------------------------------------


def test_prior_experience_threshold():
    at_minimum = deepcopy(SELF_EMPLOYED_ANSWERS)
    at_minimum["work.prior_experience_months"] = "6"
    eligibility = evaluate_eligibility(_to_answers_payload(at_minimum))
    assert "prior_experience_below_minimum" not in eligibility["failed_requirements"]

    below_minimum = deepcopy(SELF_EMPLOYED_ANSWERS)
    below_minimum["work.prior_experience_months"] = "5"
    eligibility = evaluate_eligibility(_to_answers_payload(below_minimum))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert "prior_experience_below_minimum" in eligibility["failed_requirements"]


def test_prior_experience_missing_is_needs_review():
    answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    del answers["work.prior_experience_months"]
    eligibility = evaluate_eligibility(_to_answers_payload(answers))
    assert eligibility["eligibility_status"] == "needs_review"
    assert "prior_experience_needs_review" in eligibility["failed_requirements"]


# ---------------------------------------------------------------------------
# 6. Income (consolidated)
# ---------------------------------------------------------------------------


def test_income_field_canonical_wording():
    field = _fields_by_key()["financial.annual_work_income_eur"]
    assert (
        field["label"]
        == "What annual income in EUR do you earn from the remote work you will perform while living in Italy?"
    )


def test_income_threshold():
    at_minimum = deepcopy(SELF_EMPLOYED_ANSWERS)
    at_minimum["financial.annual_work_income_eur"] = "25500"
    eligibility = evaluate_eligibility(_to_answers_payload(at_minimum))
    assert "income_below_minimum" not in eligibility["failed_requirements"]

    below_minimum = deepcopy(SELF_EMPLOYED_ANSWERS)
    below_minimum["financial.annual_work_income_eur"] = "25499"
    eligibility = evaluate_eligibility(_to_answers_payload(below_minimum))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert "income_below_minimum" in eligibility["failed_requirements"]


def test_income_missing_or_unparseable_is_needs_review():
    missing = deepcopy(SELF_EMPLOYED_ANSWERS)
    del missing["financial.annual_work_income_eur"]
    eligibility = evaluate_eligibility(_to_answers_payload(missing))
    assert eligibility["eligibility_status"] == "needs_review"
    assert "income_needs_review" in eligibility["failed_requirements"]

    unparseable = deepcopy(SELF_EMPLOYED_ANSWERS)
    unparseable["financial.annual_work_income_eur"] = "not-a-number"
    eligibility = evaluate_eligibility(_to_answers_payload(unparseable))
    assert eligibility["eligibility_status"] == "needs_review"
    assert "income_needs_review" in eligibility["failed_requirements"]


def test_income_source_fields_and_codes_absent():
    live_keys = {f["key"] for f in _load_questions()["taxonomy_fields"]}
    assert "financial.income_from_remote_work_confirmed" not in live_keys
    assert "financial.non_remote_income_source" not in live_keys
    assert "financial.income_evidence_types" not in live_keys

    assert "income_source_needs_review" not in HARD_FAILURES
    assert "passive_income_not_accepted" not in HARD_FAILURES

    source_text = RULES_PATH.read_text(encoding="utf-8")
    assert '"income_source_needs_review"' not in source_text
    assert '"passive_income_not_accepted"' not in source_text
    assert '"income_evidence_needs_review"' not in source_text


# ---------------------------------------------------------------------------
# 7. Self-employed proof removal
# ---------------------------------------------------------------------------


def test_self_employed_path_has_no_branch_specific_question():
    result, asked_keys = _walk_italy_dnv(SELF_EMPLOYED_ANSWERS)
    assert not any(key.startswith("role.digital_nomad.") for key in asked_keys)
    assert not any(key.startswith("role.remote_worker.") for key in asked_keys)


def test_self_employment_proof_field_and_codes_absent():
    live_keys = {f["key"] for f in _load_questions()["taxonomy_fields"]}
    assert "role.digital_nomad.self_employment_proof_available" not in live_keys

    assert "digital_nomad_self_employment_proof_unavailable" not in HARD_FAILURES
    source_text = RULES_PATH.read_text(encoding="utf-8")
    assert '"digital_nomad_self_employment_proof_unavailable"' not in source_text
    assert '"digital_nomad_self_employment_proof_needs_review"' not in source_text


# ---------------------------------------------------------------------------
# 8/9. Employee / Collaborator branch
# ---------------------------------------------------------------------------


def test_contract_and_declaration_only_on_employee_route():
    fields_by_key = _fields_by_key()
    assert fields_by_key["role.remote_worker.contract_available"]["applies_when"] == {
        "equals": ["routing.worker_category", "employee_or_collaborator"]
    }
    assert fields_by_key["role.remote_worker.employer_clean_record_declaration_available"][
        "applies_when"
    ] == {"equals": ["routing.worker_category", "employee_or_collaborator"]}

    _, self_employed_keys = _walk_italy_dnv(SELF_EMPLOYED_ANSWERS)
    assert "role.remote_worker.contract_available" not in self_employed_keys
    assert (
        "role.remote_worker.employer_clean_record_declaration_available"
        not in self_employed_keys
    )


def test_contract_available_behavior():
    yes_answers = deepcopy(REMOTE_WORKER_ANSWERS)
    yes_answers["role.remote_worker.contract_available"] = "yes"
    eligibility = evaluate_eligibility(_to_answers_payload(yes_answers))
    assert "remote_worker_contract_unavailable" not in eligibility["failed_requirements"]

    no_answers = deepcopy(REMOTE_WORKER_ANSWERS)
    no_answers["role.remote_worker.contract_available"] = "no"
    eligibility = evaluate_eligibility(_to_answers_payload(no_answers))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert "remote_worker_contract_unavailable" in eligibility["failed_requirements"]


def test_employer_declaration_behavior():
    yes_answers = deepcopy(REMOTE_WORKER_ANSWERS)
    yes_answers["role.remote_worker.employer_clean_record_declaration_available"] = "yes"
    eligibility = evaluate_eligibility(_to_answers_payload(yes_answers))
    assert (
        "remote_worker_employer_clean_record_unavailable"
        not in eligibility["failed_requirements"]
    )

    no_answers = deepcopy(REMOTE_WORKER_ANSWERS)
    no_answers["role.remote_worker.employer_clean_record_declaration_available"] = "no"
    eligibility = evaluate_eligibility(_to_answers_payload(no_answers))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert (
        "remote_worker_employer_clean_record_unavailable"
        in eligibility["failed_requirements"]
    )


# ---------------------------------------------------------------------------
# 11. Health insurance
# ---------------------------------------------------------------------------


def test_health_insurance_canonical_choices():
    field = _fields_by_key()["routing.health_insurance_status"]
    assert field["choices"] == ["yes", "no"]
    assert (
        field["label"]
        == "Will you have health insurance covering medical care and hospitalization in Italy for the full stay period?"
    )


def test_health_insurance_behavior():
    yes_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    yes_answers["routing.health_insurance_status"] = "yes"
    eligibility = evaluate_eligibility(_to_answers_payload(yes_answers))
    assert eligibility["eligibility_status"] == "eligible"

    no_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    no_answers["routing.health_insurance_status"] = "no"
    eligibility = evaluate_eligibility(_to_answers_payload(no_answers))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert "health_insurance_unavailable" in eligibility["failed_requirements"]

    missing_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    missing_answers["routing.health_insurance_status"] = ""
    eligibility = evaluate_eligibility(_to_answers_payload(missing_answers))
    assert eligibility["eligibility_status"] == "needs_review"
    assert "health_insurance_needs_review" in eligibility["failed_requirements"]


def test_health_insurance_old_values_absent():
    field = _fields_by_key()["routing.health_insurance_status"]
    for old_value in ("have_it", "will_obtain", "cannot_obtain"):
        assert old_value not in field["choices"]


# ---------------------------------------------------------------------------
# 12. Accommodation
# ---------------------------------------------------------------------------


def test_accommodation_canonical_choices():
    field = _fields_by_key()["housing.accommodation_status"]
    assert field["choices"] == ["yes", "no"]
    assert (
        field["label"]
        == "Will you have suitable accommodation arranged in Italy for the visa period?"
    )


def test_accommodation_behavior():
    yes_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    yes_answers["housing.accommodation_status"] = "yes"
    eligibility = evaluate_eligibility(_to_answers_payload(yes_answers))
    assert eligibility["eligibility_status"] == "eligible"

    no_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    no_answers["housing.accommodation_status"] = "no"
    eligibility = evaluate_eligibility(_to_answers_payload(no_answers))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert "accommodation_unavailable" in eligibility["failed_requirements"]

    missing_answers = deepcopy(SELF_EMPLOYED_ANSWERS)
    missing_answers["housing.accommodation_status"] = ""
    eligibility = evaluate_eligibility(_to_answers_payload(missing_answers))
    assert eligibility["eligibility_status"] == "needs_review"
    assert "accommodation_needs_review" in eligibility["failed_requirements"]


def test_accommodation_old_values_absent():
    field = _fields_by_key()["housing.accommodation_status"]
    for old_value in (
        "have_qualifying_accommodation",
        "will_secure_before_travel",
        "not_available",
    ):
        assert old_value not in field["choices"]


# ---------------------------------------------------------------------------
# 13/14. Passport
# ---------------------------------------------------------------------------


def test_passport_validity_canonical_wording():
    field = _fields_by_key()["routing.passport_validity_months"]
    assert (
        field["label"]
        == "How many months will your passport remain valid beyond your intended stay in Italy?"
    )


def test_passport_validity_tiers():
    missing = deepcopy(SELF_EMPLOYED_ANSWERS)
    del missing["routing.passport_validity_months"]
    eligibility = evaluate_eligibility(_to_answers_payload(missing))
    assert eligibility["eligibility_status"] == "needs_review"
    assert "passport_validity_needs_review" in eligibility["failed_requirements"]

    below_minimum = deepcopy(SELF_EMPLOYED_ANSWERS)
    below_minimum["routing.passport_validity_months"] = "2"
    eligibility = evaluate_eligibility(_to_answers_payload(below_minimum))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert "passport_validity_below_minimum" in eligibility["failed_requirements"]

    consular_tier = deepcopy(SELF_EMPLOYED_ANSWERS)
    consular_tier["routing.passport_validity_months"] = "10"
    eligibility = evaluate_eligibility(_to_answers_payload(consular_tier))
    assert eligibility["eligibility_status"] == "needs_review"
    assert (
        "passport_validity_consular_threshold_needs_review"
        in eligibility["failed_requirements"]
    )

    at_consular_threshold = deepcopy(SELF_EMPLOYED_ANSWERS)
    at_consular_threshold["routing.passport_validity_months"] = "15"
    eligibility = evaluate_eligibility(_to_answers_payload(at_consular_threshold))
    assert "passport_validity_below_minimum" not in eligibility["failed_requirements"]
    assert (
        "passport_validity_consular_threshold_needs_review"
        not in eligibility["failed_requirements"]
    )


def test_passport_blank_pages_absent():
    live_keys = {f["key"] for f in _load_questions()["taxonomy_fields"]}
    assert "routing.passport_blank_pages" not in live_keys

    source_text = RULES_PATH.read_text(encoding="utf-8")
    assert '"passport_blank_pages_needs_review"' not in source_text
    assert '"passport_blank_pages_below_minimum"' not in source_text


# ---------------------------------------------------------------------------
# 15/16. Family
# ---------------------------------------------------------------------------


def test_family_reunification_intent_exact_three_values():
    field = _fields_by_key()["routing.family_reunification_intent"]
    assert field["choices"] == [
        "no_one_else",
        "spouse_or_minor_children",
        "adult_children_or_parents",
    ]
    assert field["label"] == "Who will be included with you?"


def test_family_reunification_intent_behavior():
    no_one_else = deepcopy(SELF_EMPLOYED_ANSWERS)
    no_one_else["routing.family_reunification_intent"] = "no_one_else"
    eligibility = evaluate_eligibility(_to_answers_payload(no_one_else))
    assert eligibility["eligibility_status"] == "eligible"

    spouse_or_minor_children = deepcopy(SELF_EMPLOYED_ANSWERS)
    spouse_or_minor_children["routing.family_reunification_intent"] = (
        "spouse_or_minor_children"
    )
    eligibility = evaluate_eligibility(_to_answers_payload(spouse_or_minor_children))
    assert eligibility["eligibility_status"] == "eligible"

    adult_children_or_parents = deepcopy(SELF_EMPLOYED_ANSWERS)
    adult_children_or_parents["routing.family_reunification_intent"] = (
        "adult_children_or_parents"
    )
    eligibility = evaluate_eligibility(_to_answers_payload(adult_children_or_parents))
    assert eligibility["eligibility_status"] == "not_eligible"
    assert (
        "adult_children_or_parents_family_route_not_supported"
        in eligibility["failed_requirements"]
    )

    missing = deepcopy(SELF_EMPLOYED_ANSWERS)
    del missing["routing.family_reunification_intent"]
    eligibility = evaluate_eligibility(_to_answers_payload(missing))
    assert eligibility["eligibility_status"] == "needs_review"
    assert "family_reunification_needs_review" in eligibility["failed_requirements"]


def test_family_documents_available_absent():
    live_keys = {f["key"] for f in _load_questions()["taxonomy_fields"]}
    assert "routing.family_documents_available" not in live_keys

    source_text = RULES_PATH.read_text(encoding="utf-8")
    assert '"family_documents_needs_review"' not in source_text


def test_additional_information_absent():
    live_keys = {f["key"] for f in _load_questions()["taxonomy_fields"]}
    assert "routing.additional_information" not in live_keys


# ---------------------------------------------------------------------------
# Post-eligibility items
# ---------------------------------------------------------------------------


def test_relocated_questions_never_appear_in_eligibility_flow():
    for answers in (SELF_EMPLOYED_ANSWERS, REMOTE_WORKER_ANSWERS):
        _, asked_keys = _walk_italy_dnv(answers)
        for relocated_key in RELOCATED_KEYS:
            assert relocated_key not in asked_keys


def test_relocated_questions_removed_from_questions_json():
    data = _load_questions()
    live_keys = {field["key"] for field in data["taxonomy_fields"]}
    for relocated_key in RELOCATED_KEYS:
        assert relocated_key not in live_keys

    checklist_keys = {
        field["key"] for field in data["post_eligibility_checklist"]["fields"]
    }
    assert checklist_keys == RELOCATED_KEYS


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


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------


def test_hard_failures_set_exactly_eleven_intended_codes():
    assert HARD_FAILURES == EXPECTED_HARD_FAILURES
    assert len(HARD_FAILURES) == 11


def test_removed_hard_and_soft_codes_absent_from_hard_failures():
    for code in REMOVED_CODES:
        assert code not in HARD_FAILURES


def test_no_not_sure_choices_remain_anywhere_in_the_live_flow():
    data = _load_questions()
    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    for field in data["taxonomy_fields"]:
        choices = {str(c) for c in field.get("choices", [])}
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_no_phantom_or_orphaned_live_codes():
    rules_src = RULES_PATH.read_text(encoding="utf-8")
    codes_in_rules = set(
        re.findall(r'failed_requirements\.append\(\s*"([a-z0-9_]+)"\s*\)', rules_src)
    )
    codes_in_hardfail = set(
        re.findall(
            r'"([a-z0-9_]+)"',
            re.search(r"HARD_FAILURES = \{(.*?)\}", rules_src, re.S).group(1),
        )
    )

    clar = json.loads(CLARIFICATIONS_PATH.read_text(encoding="utf-8"))
    clar_codes = {c["requirement"] for c in clar["clarifications"]}
    inert_codes = {
        c["requirement"]
        for c in clar["clarifications"]
        if c.get("stage") == "post_eligibility_checklist"
    }

    out = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    out_summary_codes = set(out["summary_statement"]["requirement_variants"].keys())
    out_cta_codes = set(out["next_steps_cta"]["requirement_variants"].keys())

    assert codes_in_hardfail - codes_in_rules == set()
    assert codes_in_rules - clar_codes == set()
    assert clar_codes - codes_in_rules - inert_codes == set()
    assert out_summary_codes - codes_in_rules - inert_codes == set()
    assert out_cta_codes - codes_in_rules - inert_codes == set()
