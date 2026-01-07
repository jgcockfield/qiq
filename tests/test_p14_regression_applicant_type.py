from app.engine.evaluator import evaluate


BASE_PAYLOAD = {
    "routing": {
        "work_relationship": "contractor",
        "income_foreign_only": True,
        "passport_validity_months": 12,
        "health_insurance_status": "will_obtain",
        "background_check_available": True,
        "criminal_record_flag": False,
    },
    "identity": {"full_name": "E2E Test", "nationality": "United States"},
    "income": {"monthly_amount": 10000},
    "role": {"contractor": {"income_evidence_months": 36}},
}


def _get_rule(result: dict, rule_id: str) -> dict:
    return next(r for r in result["rule_results"] if r.get("rule_id") == rule_id)


def test_blocks_on_missing_applicant_type():
    # applicant_type omitted on purpose
    payload = {
        **BASE_PAYLOAD,
        "routing": {**BASE_PAYLOAD["routing"]},
    }
    result = evaluate(payload)

    assert "routing.applicant_type" in result["missing_fields"]
    assert result["next_field_key"] == "routing.applicant_type"


def test_passes_threshold_when_applicant_type_individual():
    payload = {
        **BASE_PAYLOAD,
        "routing": {**BASE_PAYLOAD["routing"], "applicant_type": "individual"},
    }
    result = evaluate(payload)

    assert result["missing_fields"] == []
    assert result["next_field_key"] is None

    r = _get_rule(result, "DN_MIN_MONTHLY_INCOME")
    assert r["status"] == "pass"


def test_fails_honestly_when_applicant_type_invalid():
    payload = {
        **BASE_PAYLOAD,
        "routing": {**BASE_PAYLOAD["routing"], "applicant_type": "contractor"},  # invalid enum
    }
    result = evaluate(payload)

    assert result["missing_fields"] == []
    assert result["next_field_key"] is None

    r = _get_rule(result, "DN_MIN_MONTHLY_INCOME")
    assert r["status"] == "needs_review"
    assert r["reason"] == "Applicant type threshold not available."
