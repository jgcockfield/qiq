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


VALID_SPAIN_DNV_ANSWERS = {
    "routing.country": "spain",
    "routing.pathway": "spain_dnv",
    "routing.service_interest": "digital_nomad_visa",
    "routing.work_relationship": "employee",
    "role.profession_description": "Software Engineer",
    "routing.income_foreign_only": "yes",
    "role.employee.gross_monthly_income_band_eur": "eur_5000_10000",
    "role.employee.income_evidence_types": [
        "bank_statements",
        "employment_contract",
        "pay_stubs",
    ],
    "role.employee.income_evidence_months": "12_or_more",
    "routing.passport_validity_months": "24",
    "documents.police_clearance_available": "yes",
    "routing.criminal_record_flag": "no",
    "routing.health_insurance_status": "will_obtain",
    "routing.has_dependents": "no",
    "identity.first_name": "Sofia",
    "identity.last_name": "Navarro",
    "phone": "+15551234567",
    "email": "sofia@example.com",
    "identity.nationality": "United States",
    "identity.country_of_residence": "United States of America",
    "documents.civil_documents_available": "yes",
    "documents.apostille_translation_ready": "yes",
    "routing.renewal_compliance_acknowledged": "yes",
    "consent.terms_conditions": "yes",
    "consent.privacy_policy": "yes",
    "consent.judicial_data_processing": "yes",
    "consent.marketing": "no",
}


def test_spain_dnv_valid_applicant_full_evaluate_flow(client):
    body, asked_keys = _walk_spain_dnv_flow(client, VALID_SPAIN_DNV_ANSWERS)

    assert asked_keys == [
        "routing.country",
        "routing.pathway",
        "routing.service_interest",
        "routing.work_relationship",
        "role.profession_description",
        "routing.income_foreign_only",
        "role.employee.gross_monthly_income_band_eur",
        "role.employee.income_evidence_types",
        "role.employee.income_evidence_months",
        "routing.has_dependents",
        "identity.nationality",
        "identity.country_of_residence",
        "routing.passport_validity_months",
        "routing.health_insurance_status",
        "documents.police_clearance_available",
        "routing.criminal_record_flag",
        "documents.civil_documents_available",
        "documents.apostille_translation_ready",
        "routing.renewal_compliance_acknowledged",
        "identity.first_name",
        "identity.last_name",
        "phone",
        "email",
        "consent.terms_conditions",
        "consent.privacy_policy",
        "consent.judicial_data_processing",
        "consent.marketing",
    ]
    assert "routing.applicant_type" not in asked_keys
    assert "routing.income_foreign_only" in asked_keys

    result = body["result"]
    assert result["meta"]["status"] == "eligible"
    assert result["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert "Spain's Digital Nomad Visa" in result["summary"]
    assert result["next_steps"]["action"]["type"] == "consultation"
    assert result["next_steps"]["action"]["label"] == "Book a Spain DNV consultation"
    assert result["clarifications"] == []


def test_spain_dnv_below_2800_full_evaluate_flow_returns_not_eligible(client):
    answers = deepcopy(VALID_SPAIN_DNV_ANSWERS)
    answers["role.employee.gross_monthly_income_band_eur"] = "below_2800"

    body, asked_keys = _walk_spain_dnv_flow(client, answers)

    assert asked_keys[0] == "routing.country"
    assert asked_keys[1] == "routing.pathway"
    assert asked_keys[2] == "routing.service_interest"
    result = body["result"]
    assert result["meta"]["status"] == "not_eligible"
    assert result["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert "do not currently appear to meet" in result["summary"]
    assert result["next_steps"]["action"]["type"] == "informational"
    assert result["clarifications"][0]["requirement"] == "income_below_minimum"
    assert "minimum qualifying band" in result["clarifications"][0]["clarification"]


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


def test_stage_one_selector_over_api(client):
    first = _post_evaluate(client, {"session_id": "test-selector"})
    assert first["next_field_key"] == "routing.country"
    assert first["field"]["choices"] == ["spain", "costa_rica"]

    spain = _post_evaluate(
        client,
        {"session_id": "test-selector", "routing": {"country": "spain"}},
    )
    assert spain["next_field_key"] == "routing.pathway"
    assert spain["field"]["choices"] == ["spain_dnv"]

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
    assert spain_next["next_field_key"] == "routing.service_interest"

    costa_next = _post_evaluate(
        client,
        {"session_id": "test-selector", "routing": {"country": "costa_rica", "pathway": "costa_rica_dnv"}},
    )
    assert costa_next["next_field_key"] == "routing.work_relationship"
