from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

import pytest


def _import_fastapi_app():
    mod = __import__("main", fromlist=["app"])
    return getattr(mod, "app")


@pytest.fixture(scope="session")
def client():
    try:
        from fastapi.testclient import TestClient

        return TestClient(_import_fastapi_app())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Skipping API tests: FastAPI app/TestClient not available. {exc}")


def _set_dotted(payload: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cur = payload
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def _post_evaluate(client, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _walk_spain_dnv_flow(client, answers: Dict[str, Any]) -> tuple[Dict[str, Any], list[str]]:
    payload: Dict[str, Any] = {
        "session_id": "test-spain-dnv-e2e",
    }
    asked_keys: list[str] = []

    for _ in range(60):
        body = _post_evaluate(client, payload)
        next_key = body.get("next_field_key")
        if next_key is None:
            return body, asked_keys

        asked_keys.append(next_key)
        assert next_key in answers, f"Missing test answer for {next_key}"
        _set_dotted(payload, next_key, answers[next_key])

    raise AssertionError("Spain DNV flow did not terminate within 30 steps")


def _walk_spain_dnv_until(
    client, answers: Dict[str, Any], until_key: str
) -> Dict[str, Any]:
    """Walk the flow, answering questions from `answers`, and return the
    response body at the point `until_key` is asked (without answering it)."""
    payload: Dict[str, Any] = {
        "session_id": "test-spain-dnv-e2e-until",
    }

    for _ in range(60):
        body = _post_evaluate(client, payload)
        next_key = body.get("next_field_key")
        if next_key == until_key:
            return body
        if next_key is None:
            raise AssertionError(f"Flow ended without asking {until_key}")

        assert next_key in answers, f"Missing test answer for {next_key}"
        _set_dotted(payload, next_key, answers[next_key])

    raise AssertionError(f"Spain DNV flow did not reach {until_key} within 60 steps")


VALID_SPAIN_DNV_ANSWERS = {
    "routing.country": "spain",
    "routing.pathway": "spain_dnv",
    "routing.work_relationship": "employee",
    "routing.applicant_type": "individual",
    "role.employee.employer_outside_spain": "yes",
    "role.employee.foreign_employment_months": "12",
    "role.employee.remote_work_approved": "yes",
    "role.employee.employer_company_operating_1_year": "yes",
    "role.employee.qualification_or_experience": "qualifying_education",
    "role.employee.monthly_income_eur": "5000",
    "role.employee.income_evidence_types": [
        "bank_statements",
        "employment_contract",
        "pay_stubs",
    ],
    "role.employee.income_evidence_months": "12_or_more",
    "identity.nationality": "United States",
    "routing.passport_validity_months": "24",
    "routing.health_insurance_status": "will_obtain",
    "documents.police_clearance_available": "yes",
    "routing.criminal_record_flag": "no",
}


def test_spain_dnv_valid_applicant_full_evaluate_flow(client):
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_ANSWERS)

    assert asked_keys == [
        "routing.country",
        "routing.pathway",
        "routing.work_relationship",
        "routing.applicant_type",
        "role.employee.employer_outside_spain",
        "role.employee.foreign_employment_months",
        "role.employee.remote_work_approved",
        "role.employee.employer_company_operating_1_year",
        "role.employee.qualification_or_experience",
        "role.employee.monthly_income_eur",
        "role.employee.income_evidence_types",
        "role.employee.income_evidence_months",
        "identity.nationality",
        "routing.passport_validity_months",
        "routing.health_insurance_status",
        "documents.police_clearance_available",
        "routing.criminal_record_flag",
    ]
    assert "routing.service_interest" not in asked_keys
    assert "role.profession_description" not in asked_keys
    assert "documents.civil_documents_available" not in asked_keys
    assert "consent.terms_conditions" not in asked_keys
    assert "routing.supporting_company_operating_1_year" not in asked_keys
    assert "routing.additional_information" not in asked_keys

    result = body["result"]
    assert result["meta"]["status"] == "eligible"
    assert result["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert "Spain's Digital Nomad Visa" in result["summary"]
    assert result["next_steps"]["action"]["type"] == "consultation"
    assert result["next_steps"]["action"]["label"] == "Book a Spain DNV consultation"
    assert result["clarifications"] == []


def test_spain_dnv_employee_income_at_2026_smi_threshold_is_eligible(client):
    """200% of the 2026 SMI (EUR 1,221) = EUR 2,442/month for an individual
    Employee applicant -- the new formula-based threshold, replacing the old
    flat EUR 2,800 minimum for Employee only."""
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.monthly_income_eur"] = "2442"

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_employee_income_below_2026_smi_threshold_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.monthly_income_eur"] = "2441"

    body, asked_keys = _walk_spain_dnv_flow(client, answers)

    assert asked_keys[0] == "routing.country"
    assert asked_keys[1] == "routing.pathway"
    assert asked_keys[2] == "routing.work_relationship"
    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert result["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert "do not currently appear to meet" in result["summary"]
    assert result["next_steps"]["action"]["type"] == "informational"
    assert result["clarifications"][0]["requirement"] == "employee_income_below_minimum"


VALID_SPAIN_DNV_CONTRACTOR_ANSWERS = {
    "routing.country": "spain",
    "routing.pathway": "spain_dnv",
    "routing.work_relationship": "contractor",
    "routing.applicant_type": "individual",
    "role.contractor.monthly_income_eur": "4000",
    "role.contractor.foreign_client_relationship": "yes",
    "role.contractor.foreign_client_relationship_months": "12",
    "role.contractor.remote_work_capable": "yes",
    "role.contractor.foreign_company_operating_1_year": "yes",
    "role.contractor.qualification_or_experience": "qualifying_education",
    "role.contractor.spanish_clients_flag": "no",
    "role.contractor.income_evidence_types": [
        "bank_statements",
        "service_agreements_or_contracts",
        "invoices",
    ],
    "role.contractor.income_evidence_months": "12_or_more",
    "identity.nationality": "United States",
    "routing.passport_validity_months": "24",
    "routing.health_insurance_status": "will_obtain",
    "documents.police_clearance_available": "yes",
    "routing.criminal_record_flag": "no",
}


def test_spain_dnv_contractor_full_evaluate_flow(client):
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)

    assert asked_keys == [
        "routing.country",
        "routing.pathway",
        "routing.work_relationship",
        "routing.applicant_type",
        "role.contractor.monthly_income_eur",
        "role.contractor.foreign_client_relationship",
        "role.contractor.foreign_client_relationship_months",
        "role.contractor.remote_work_capable",
        "role.contractor.foreign_company_operating_1_year",
        "role.contractor.qualification_or_experience",
        "role.contractor.spanish_clients_flag",
        "role.contractor.income_evidence_types",
        "role.contractor.income_evidence_months",
        "identity.nationality",
        "routing.passport_validity_months",
        "routing.health_insurance_status",
        "documents.police_clearance_available",
        "routing.criminal_record_flag",
    ]
    assert not any(key.startswith("role.employee.") for key in asked_keys)
    assert not any(key.startswith("role.business_owner.") for key in asked_keys)
    assert "role.contractor.service_agreements_available" not in asked_keys
    assert "routing.supporting_company_operating_1_year" not in asked_keys

    result = body["result"]
    assert result["meta"]["status"] == "eligible"
    assert result["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert result["clarifications"] == []


def test_spain_dnv_contractor_income_at_2026_smi_threshold_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.monthly_income_eur"] = "2442"

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_contractor_income_below_2026_smi_threshold_returns_not_eligible(
    client,
):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.monthly_income_eur"] = "2441"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert result["clarifications"][0]["requirement"] == "contractor_income_below_minimum"


def test_spain_dnv_contractor_remote_work_not_possible_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.remote_work_capable"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert result["clarifications"][0]["requirement"] == "contractor_remote_work_not_possible"


def test_spain_dnv_contractor_foreign_company_below_1_year_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.foreign_company_operating_1_year"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "supporting_company_operating_history_below_minimum"
    )


def test_spain_dnv_contractor_qualifying_education_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.qualification_or_experience"] = "qualifying_education"

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_contractor_3_years_experience_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.qualification_or_experience"] = (
        "3_or_more_years_of_relevant_professional_experience"
    )

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_contractor_neither_qualification_nor_experience_returns_not_eligible(
    client,
):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.qualification_or_experience"] = "neither"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "contractor_qualification_or_experience_not_met"
    )


VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS = {
    "routing.country": "spain",
    "routing.pathway": "spain_dnv",
    "routing.work_relationship": "business_owner",
    "routing.applicant_type": "individual",
    "role.business_owner.monthly_income_eur": "6000",
    "role.business_owner.business_outside_spain": "yes",
    "role.business_owner.months_owned_operated": "12",
    "role.business_owner.remote_operation_capable": "yes",
    "role.business_owner.business_operating_1_year": "yes",
    "role.business_owner.qualification_or_experience": "qualifying_education",
    "role.business_owner.spanish_clients_flag": "no",
    "role.business_owner.income_evidence_types": [
        "bank_statements",
        "business_registration",
        "tax_returns_or_financial_statements",
    ],
    "role.business_owner.income_evidence_months": "12_or_more",
    "identity.nationality": "United States",
    "routing.passport_validity_months": "24",
    "routing.health_insurance_status": "will_obtain",
    "documents.police_clearance_available": "yes",
    "routing.criminal_record_flag": "no",
}


def test_spain_dnv_business_owner_full_evaluate_flow(client):
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)

    assert asked_keys == [
        "routing.country",
        "routing.pathway",
        "routing.work_relationship",
        "routing.applicant_type",
        "role.business_owner.monthly_income_eur",
        "role.business_owner.business_outside_spain",
        "role.business_owner.months_owned_operated",
        "role.business_owner.remote_operation_capable",
        "role.business_owner.business_operating_1_year",
        "role.business_owner.qualification_or_experience",
        "role.business_owner.spanish_clients_flag",
        "role.business_owner.income_evidence_types",
        "role.business_owner.income_evidence_months",
        "identity.nationality",
        "routing.passport_validity_months",
        "routing.health_insurance_status",
        "documents.police_clearance_available",
        "routing.criminal_record_flag",
    ]
    assert not any(key.startswith("role.employee.") for key in asked_keys)
    assert not any(key.startswith("role.contractor.") for key in asked_keys)
    assert "role.business_owner.work_structure" not in asked_keys
    assert "routing.supporting_company_operating_1_year" not in asked_keys

    result = body["result"]
    assert result["meta"]["status"] == "eligible"
    assert result["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert result["clarifications"] == []


def test_spain_dnv_business_owner_no_work_structure_question_and_no_old_choices(client):
    """The old subrouting question and its two choices no longer exist
    anywhere in the live Business Owner flow."""
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)

    assert "role.business_owner.work_structure" not in asked_keys

    import json
    from pathlib import Path

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_dnv"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    all_choices = {
        choice
        for field in data["taxonomy_fields"]
        for choice in (field.get("choices") or [])
    }
    assert "salary_as_employee" not in all_choices
    assert "business_or_self_employment_income" not in all_choices


def test_spain_dnv_business_owner_business_in_spain_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.business_outside_spain"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "business_owner_business_located_in_spain"
    )


def test_spain_dnv_business_owner_ownership_below_3_months_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.months_owned_operated"] = "2"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "business_owner_ownership_duration_below_minimum"
    )


def test_spain_dnv_business_owner_ownership_at_3_months_is_not_a_failure(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.months_owned_operated"] = "3"

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_business_owner_remote_operation_not_possible_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.remote_operation_capable"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "business_owner_remote_operation_not_possible"
    )


def test_spain_dnv_business_owner_below_1_year_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.business_operating_1_year"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "supporting_company_operating_history_below_minimum"
    )


def test_spain_dnv_business_owner_qualifying_education_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.qualification_or_experience"] = "qualifying_education"

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_business_owner_3_years_experience_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.qualification_or_experience"] = (
        "3_or_more_years_of_relevant_professional_experience"
    )

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_business_owner_neither_qualification_nor_experience_returns_not_eligible(
    client,
):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.qualification_or_experience"] = "neither"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "business_owner_qualification_or_experience_not_met"
    )


def test_spain_dnv_business_owner_income_at_2026_smi_threshold_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.monthly_income_eur"] = "2442"

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_business_owner_income_below_2026_smi_threshold_returns_not_eligible(
    client,
):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.monthly_income_eur"] = "2441"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"] == "business_owner_income_below_minimum"
    )


def test_spain_dnv_business_owner_no_spanish_clients_does_not_ask_percentage(client):
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)

    assert "role.business_owner.spanish_activity_percentage" not in asked_keys
    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_business_owner_spanish_activity_within_20_percent_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.spanish_clients_flag"] = "yes"
    answers["role.business_owner.spanish_activity_percentage"] = "20"

    body, asked_keys = _walk_spain_dnv_flow(client, answers)

    assert "role.business_owner.spanish_activity_percentage" in asked_keys
    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_business_owner_spanish_activity_above_20_percent_returns_not_eligible(
    client,
):
    answers = deepcopy(VALID_SPAIN_DNV_BUSINESS_OWNER_ANSWERS)
    answers["role.business_owner.spanish_clients_flag"] = "yes"
    answers["role.business_owner.spanish_activity_percentage"] = "21"

    body, asked_keys = _walk_spain_dnv_flow(client, answers)

    assert "role.business_owner.spanish_activity_percentage" in asked_keys
    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "business_owner_spanish_activity_above_threshold"
    )


VALID_SPAIN_DNV_FAMILY_ANSWERS = {
    "routing.country": "spain",
    "routing.pathway": "spain_dnv",
    "routing.work_relationship": "employee",
    "routing.applicant_type": "family",
    "role.employee.employer_outside_spain": "yes",
    "role.employee.foreign_employment_months": "12",
    "role.employee.remote_work_approved": "yes",
    "role.employee.employer_company_operating_1_year": "yes",
    "role.employee.qualification_or_experience": "qualifying_education",
    "role.employee.monthly_income_eur": "5000",
    "role.employee.income_evidence_types": [
        "bank_statements",
        "employment_contract",
        "pay_stubs",
    ],
    "role.employee.income_evidence_months": "12_or_more",
    "routing.dependents_count": "2",
    "routing.dependent_relationships": "Spouse, child",
    "routing.dependent_ages": "38, 9",
    "identity.nationality": "United States",
    "routing.passport_validity_months": "24",
    "routing.health_insurance_status": "will_obtain",
    "documents.police_clearance_available": "yes",
    "routing.criminal_record_flag": "no",
}


def test_spain_dnv_family_applicant_full_evaluate_flow(client):
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_FAMILY_ANSWERS)

    assert asked_keys == [
        "routing.country",
        "routing.pathway",
        "routing.work_relationship",
        "routing.applicant_type",
        "role.employee.employer_outside_spain",
        "role.employee.foreign_employment_months",
        "role.employee.remote_work_approved",
        "role.employee.employer_company_operating_1_year",
        "role.employee.qualification_or_experience",
        "role.employee.monthly_income_eur",
        "role.employee.income_evidence_types",
        "role.employee.income_evidence_months",
        "routing.dependents_count",
        "routing.dependent_relationships",
        "routing.dependent_ages",
        "identity.nationality",
        "routing.passport_validity_months",
        "routing.health_insurance_status",
        "documents.police_clearance_available",
        "routing.criminal_record_flag",
    ]

    result = body["result"]
    assert result["meta"]["status"] == "eligible"
    assert result["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert result["clarifications"] == []


def test_spain_dnv_employee_family_income_formula_uses_smi_scaling(client):
    """200% SMI + 75% SMI (first dependent) + 25% SMI (second dependent)
    = 2442 + 915.75 + 305.25 = 3663.0 EUR/month for 2 dependents."""
    answers = deepcopy(VALID_SPAIN_DNV_FAMILY_ANSWERS)

    answers["role.employee.monthly_income_eur"] = "3662"
    body, _ = _walk_spain_dnv_flow(client, answers)
    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert result["clarifications"][0]["requirement"] == "employee_income_below_minimum"

    answers["role.employee.monthly_income_eur"] = "3663"
    body, _ = _walk_spain_dnv_flow(client, answers)
    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_health_insurance_question_has_expected_choices(client):
    body = _walk_spain_dnv_until(
        client, VALID_SPAIN_DNV_ANSWERS, "routing.health_insurance_status"
    )

    assert body["field"]["input_type"] == "choice"
    assert body["field"]["choices"] == ["have_it", "will_obtain"]


def test_costa_rica_full_evaluate_behavior_still_returns_default_output(client):
    payload = {
        "pathway": "costa-rica-dnv",
        "session_id": "test-costa-rica-e2e",
        "routing": {
            "work_relationship": "contractor",
            "applicant_type": "individual",
            "income_foreign_only": "yes",
            "passport_validity_months": "12",
            "health_insurance_status": "have_it",
            "background_check_available": "yes",
            "criminal_record_flag": "no",
        },
        "identity": {"nationality": "United States"},
        "role": {
            "contractor": {
                "monthly_income_usd": "3500",
                "income_evidence_types": [
                    "bank_statements",
                    "invoices",
                    "contracts",
                    "tax_returns",
                ],
                "income_evidence_months": "12",
            }
        },
    }

    body = _post_evaluate(client, payload)

    assert body["next_field_key"] is None
    assert body["result"]["meta"]["status"] == "eligible"
    assert body["result"]["meta"]["visa_type"] == "Digital Nomad"
    assert body["result"]["summary"] == "Based on the information provided, you meet the eligibility requirements."
    assert body["result"]["next_steps"]["action"]["label"] == "Book a consultation with Great Expatations"


def test_spain_dnv_employee_employer_in_spain_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.employer_outside_spain"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert result["clarifications"][0]["requirement"] == "employee_employer_located_in_spain"


def test_spain_dnv_employee_foreign_employment_below_3_months_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.foreign_employment_months"] = "2"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "employee_foreign_employment_duration_below_minimum"
    )


def test_spain_dnv_employee_foreign_employment_at_3_months_is_not_a_failure(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.foreign_employment_months"] = "3"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "eligible"


def test_spain_dnv_employee_remote_work_not_approved_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.remote_work_approved"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert result["clarifications"][0]["requirement"] == "employee_remote_work_not_approved"


def test_spain_dnv_employee_employer_company_below_1_year_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.employer_company_operating_1_year"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "supporting_company_operating_history_below_minimum"
    )


def test_spain_dnv_employee_qualifying_education_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.qualification_or_experience"] = "qualifying_education"

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_employee_3_years_experience_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.qualification_or_experience"] = (
        "3_or_more_years_of_relevant_professional_experience"
    )

    body, _ = _walk_spain_dnv_flow(client, answers)

    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_employee_neither_qualification_nor_experience_returns_not_eligible(
    client,
):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.qualification_or_experience"] = "neither"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "employee_qualification_or_experience_not_met"
    )


def test_spain_dnv_contractor_without_foreign_client_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.foreign_client_relationship"] = "no"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "contractor_foreign_client_relationship_missing"
    )


def test_spain_dnv_contractor_foreign_client_below_3_months_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.foreign_client_relationship_months"] = "2"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "contractor_foreign_client_duration_below_minimum"
    )


def test_spain_dnv_contractor_foreign_client_at_3_months_is_not_a_failure(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.foreign_client_relationship_months"] = "3"

    body, _ = _walk_spain_dnv_flow(client, answers)

    result = body["result"]
    assert result["meta"]["status"] == "eligible"


def test_spain_dnv_contractor_no_spanish_clients_does_not_ask_percentage(client):
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)

    assert "role.contractor.spanish_activity_percentage" not in asked_keys
    assert body["result"]["meta"]["status"] == "eligible"


def test_spain_dnv_contractor_spanish_activity_within_20_percent_is_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.spanish_clients_flag"] = "yes"
    answers["role.contractor.spanish_activity_percentage"] = "20"

    body, asked_keys = _walk_spain_dnv_flow(client, answers)

    assert "role.contractor.spanish_activity_percentage" in asked_keys
    result = body["result"]
    assert result["meta"]["status"] == "eligible"


def test_spain_dnv_contractor_spanish_activity_above_20_percent_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_CONTRACTOR_ANSWERS)
    answers["role.contractor.spanish_clients_flag"] = "yes"
    answers["role.contractor.spanish_activity_percentage"] = "21"

    body, asked_keys = _walk_spain_dnv_flow(client, answers)

    assert "role.contractor.spanish_activity_percentage" in asked_keys
    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert (
        result["clarifications"][0]["requirement"]
        == "contractor_spanish_activity_above_threshold"
    )


def test_spain_dnv_no_escape_choices_anywhere_in_schema():
    import json
    from pathlib import Path

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_dnv"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown"}
    for field in data["taxonomy_fields"]:
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_stage_one_selector_over_api(client):
    first = _post_evaluate(client, {"session_id": "test-selector"})
    assert first["next_field_key"] == "routing.country"
    assert first["field"]["choices"] == ["spain", "costa_rica"]

    spain = _post_evaluate(
        client,
        {"session_id": "test-selector", "routing": {"country": "spain"}},
    )
    assert spain["next_field_key"] == "routing.pathway"
    assert spain["field"]["choices"] == [
        "spain_dnv",
        "spain_nlv",
        "spain_student_visa",
    ]

    costa_rica = _post_evaluate(
        client,
        {"session_id": "test-selector", "routing": {"country": "costa_rica"}},
    )
    assert costa_rica["next_field_key"] == "routing.pathway"
    assert costa_rica["field"]["choices"] == ["costa_rica_dnv", "costa_rica_pensionado"]

    spain_next = _post_evaluate(
        client,
        {"session_id": "test-selector", "routing": {"country": "spain", "pathway": "spain_dnv"}},
    )
    assert spain_next["next_field_key"] == "routing.work_relationship"

    costa_next = _post_evaluate(
        client,
        {"session_id": "test-selector", "routing": {"country": "costa_rica", "pathway": "costa_rica_dnv"}},
    )
    assert costa_next["next_field_key"] == "routing.work_relationship"
