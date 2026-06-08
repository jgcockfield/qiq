from copy import deepcopy
from pathlib import Path

from app.engine.eligibility_rules import evaluate_eligibility
from app.engine.evaluator import evaluate
from app.engine.output_builder import build_output
from app.engine.pathway_registry import resolve_pathway


def _complete_contractor_payload():
    return {
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


def test_pathway_registry_aliases():
    assert resolve_pathway("costa-rica-dnv").canonical_id == "costa_rica_dnv"
    assert resolve_pathway("costa_rica_dnv").canonical_id == "costa_rica_dnv"
    assert resolve_pathway("spain-dnv").canonical_id == "spain_dnv"
    assert resolve_pathway("spain_dnv").canonical_id == "spain_dnv"
    assert resolve_pathway("costa-rica-pensionado").canonical_id == "costa_rica_pensionado"
    assert resolve_pathway("costa_rica_pensionado").canonical_id == "costa_rica_pensionado"
    assert resolve_pathway("spain-dnv").implemented is False
    assert resolve_pathway("spain-dnv").questions_file == "pathways/spain_dnv/questions.json"
    assert resolve_pathway("costa-rica-pensionado").implemented is True
    assert (
        resolve_pathway("costa-rica-pensionado").questions_file
        == "pathways/costa_rica_pensionado/questions.json"
    )
    assert (
        resolve_pathway("costa-rica-pensionado").rules_module
        == "app.engine.pathways.costa_rica_pensionado.rules"
    )
    assert (
        resolve_pathway("costa-rica-pensionado").output_file
        == "pathways/costa_rica_pensionado/output.json"
    )
    assert (
        resolve_pathway("costa-rica-pensionado").clarifications_file
        == "pathways/costa_rica_pensionado/clarifications.json"
    )


def test_spain_questions_file_exists():
    questions_path = Path("app/engine") / resolve_pathway("spain-dnv").questions_file
    assert questions_path.exists()


def test_stage_one_first_question_is_country():
    result = evaluate({})

    assert result["next_field_key"] == "routing.country"
    assert result["field"]["choices"] == ["spain", "costa_rica"]


def test_stage_one_spain_filters_pathway_choices():
    result = evaluate({"routing": {"country": "spain"}})

    assert result["next_field_key"] == "routing.pathway"
    assert result["field"]["choices"] == ["spain_dnv"]


def test_stage_one_costa_rica_filters_pathway_choices():
    result = evaluate({"routing": {"country": "costa_rica"}})

    assert result["next_field_key"] == "routing.pathway"
    assert result["field"]["choices"] == ["costa_rica_dnv", "costa_rica_pensionado"]


def test_stage_one_spain_pathway_continues_to_spain_questions():
    result = evaluate({"routing": {"country": "spain", "pathway": "spain_dnv"}})

    assert result["next_field_key"] == "routing.service_interest"
    assert result["field"]["choices"] == ["digital_nomad_visa", "tax_services"]


def test_stage_one_costa_rica_pathway_continues_to_existing_flow():
    result = evaluate({"routing": {"country": "costa_rica", "pathway": "costa_rica_dnv"}})

    assert result["next_field_key"] == "routing.work_relationship"
    assert result["field"]["choices"] == ["contractor", "employee", "business_owner"]


def test_costa_rica_aliases_preserve_evaluator_navigation():
    payload = {"routing": {"work_relationship": "contractor"}}
    baseline = evaluate(deepcopy(payload))

    assert evaluate(deepcopy(payload), pathway="costa-rica-dnv") == baseline
    assert evaluate(deepcopy(payload), pathway="costa_rica_dnv") == baseline


def test_costa_rica_aliases_preserve_terminal_evaluator_result():
    payload = _complete_contractor_payload()
    baseline = evaluate(deepcopy(payload))

    assert evaluate(deepcopy(payload), pathway="costa-rica-dnv") == baseline
    assert evaluate(deepcopy(payload), pathway="costa_rica_dnv") == baseline
    assert baseline == {"missing_fields": [], "next_field_key": None}


def test_costa_rica_aliases_preserve_eligibility_result():
    payload = _complete_contractor_payload()
    baseline = evaluate_eligibility(deepcopy(payload))

    assert evaluate_eligibility(deepcopy(payload), pathway="costa-rica-dnv") == baseline
    assert evaluate_eligibility(deepcopy(payload), pathway="costa_rica_dnv") == baseline
    assert baseline["eligibility_status"] == "eligible"


def _spain_payload(
    *,
    service_interest="digital_nomad_visa",
    work_relationship="employee",
    income_band="eur_2800_5000",
    foreign_income="yes",
    income_history="12_or_more",
    income_evidence_types=None,
    passport_validity_months="24",
    police_clearance_available="yes",
    criminal_record_flag="no",
    health_insurance_status="will_obtain",
    has_dependents="no",
    dependents_count="0",
    civil_documents_available="yes",
    apostille_translation_ready="yes",
    renewal_compliance_acknowledged="yes",
    service_agreements=None,
):
    if income_evidence_types is None:
        income_evidence_types = {
            "employee": ["bank_statements", "employment_contract", "pay_stubs"],
            "contractor": [
                "bank_statements",
                "service_agreements_or_contracts",
                "invoices",
            ],
            "business_owner": [
                "bank_statements",
                "business_registration",
                "tax_returns_or_financial_statements",
            ],
        }.get(work_relationship, ["bank_statements"])

    payload = {
        "routing": {
            "service_interest": service_interest,
            "work_relationship": work_relationship,
            "income_foreign_only": foreign_income,
            "passport_validity_months": passport_validity_months,
            "criminal_record_flag": criminal_record_flag,
            "health_insurance_status": health_insurance_status,
            "has_dependents": has_dependents,
            "dependents_count": dependents_count,
            "renewal_compliance_acknowledged": renewal_compliance_acknowledged,
        },
        "identity": {
            "country_of_residence": "United States of America",
            "nationality": "United States",
        },
        "income": {
            "gross_monthly_income_band_eur": income_band,
            "income_history_months": income_history,
            "income_evidence_types": income_evidence_types,
        },
        "documents": {
            "police_clearance_available": police_clearance_available,
            "civil_documents_available": civil_documents_available,
            "apostille_translation_ready": apostille_translation_ready,
        },
        "role": {},
    }
    if service_agreements is not None:
        payload["role"]["contractor"] = {
            "service_agreements_available": service_agreements,
        }
    return payload


def _pensionado_payload(
    *,
    monthly_pension_usd="1000",
    pension_foreign_source_confirmed="yes",
    pension_duration_type="lifetime_or_indefinite",
    police_clearance_available="yes",
    criminal_record_flag="no",
    pension_receipt_evidence="will_document_after_approval",
):
    return {
        "routing": {
            "applicant_type": "individual",
            "passport_validity_months": "24",
            "criminal_record_flag": criminal_record_flag,
            "no_work_authorization_acknowledged": "yes",
            "temporary_residence_acknowledged": "yes",
            "renewal_every_two_years_acknowledged": "yes",
        },
        "identity": {
            "nationality": "United States",
            "country_of_residence": "United States",
        },
        "role": {
            "pensionado": {
                "retired_from_habitual_occupation": "yes",
                "monthly_pension_usd": monthly_pension_usd,
                "pension_source_type": "social_security",
                "pension_retirement_based": "yes",
                "pension_foreign_source_confirmed": pension_foreign_source_confirmed,
                "pension_duration_type": pension_duration_type,
                "pension_certificate_available": "yes",
            }
        },
        "documents": {
            "passport_copy_available": "yes",
            "police_clearance_available": police_clearance_available,
            "birth_certificate_available": "yes",
            "passport_photos_available": "yes",
            "filiacion_form_ready": "yes",
            "request_letter_ready": "yes",
            "government_fees_ready": "yes",
            "apostille_translation_ready": "yes",
            "ccss_renewal_ready": "will_register_after_approval",
            "pension_receipt_costa_rica_evidence_available": pension_receipt_evidence,
        },
    }


def test_costa_rica_pensionado_aliases_load_first_question():
    result_dash = evaluate({}, pathway="costa-rica-pensionado")
    result_underscore = evaluate({}, pathway="costa_rica_pensionado")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "routing.applicant_type"
    assert result_dash["field"]["input_type"] == "choice"
    assert result_dash["field"]["choices"] == ["individual", "family"]


def test_costa_rica_pensionado_standard_order_after_applicant_type():
    payload = {"routing": {"applicant_type": "individual"}, "role": {"pensionado": {}}}

    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "role.pensionado.retired_from_habitual_occupation"

    payload["role"]["pensionado"]["retired_from_habitual_occupation"] = "yes"
    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "role.pensionado.pension_source_type"

    payload["role"]["pensionado"]["pension_source_type"] = "social_security"
    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "role.pensionado.pension_retirement_based"

    payload["role"]["pensionado"]["pension_retirement_based"] = "yes"
    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "routing.no_work_authorization_acknowledged"


def test_costa_rica_pensionado_uses_dnv_style_income_order():
    payload = {
        "routing": {
            "applicant_type": "individual",
            "no_work_authorization_acknowledged": "yes",
        },
        "role": {
            "pensionado": {
                "retired_from_habitual_occupation": "yes",
                "pension_source_type": "social_security",
                "pension_retirement_based": "yes",
                "pension_foreign_source_confirmed": "yes",
                "monthly_pension_usd": "1000",
            }
        },
    }

    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "role.pensionado.pension_certificate_available"

    payload["role"]["pensionado"]["pension_certificate_available"] = "yes"
    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "role.pensionado.pension_duration_type"


def test_costa_rica_pensionado_asks_dependents_before_identity_when_family():
    payload = {
        "routing": {
            "applicant_type": "family",
            "no_work_authorization_acknowledged": "yes",
        },
        "role": {
            "pensionado": {
                "retired_from_habitual_occupation": "yes",
                "pension_source_type": "social_security",
                "pension_retirement_based": "yes",
                "pension_foreign_source_confirmed": "yes",
                "monthly_pension_usd": "1000",
                "pension_certificate_available": "yes",
                "pension_duration_type": "lifetime_or_indefinite",
            }
        },
    }

    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "routing.dependents_count"

    payload["routing"]["dependents_count"] = "1"
    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "documents.dependent_documents_available"

    payload["documents"] = {"dependent_documents_available": "yes"}
    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] == "identity.nationality"


def test_costa_rica_pensionado_1000_plus_pension_can_return_eligible():
    result = evaluate_eligibility(
        _pensionado_payload(monthly_pension_usd="1000"),
        pathway="costa-rica-pensionado",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["pathway"] == "costa_rica_pensionado"
    assert result["visa_type"] == "Costa Rica Pensionado Residency"


def test_costa_rica_pensionado_below_1000_returns_not_eligible():
    result = evaluate_eligibility(
        _pensionado_payload(monthly_pension_usd="999"),
        pathway="costa_rica_pensionado",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["pension_income_below_minimum"]


def test_costa_rica_pensionado_missing_documents_returns_needs_review():
    result = evaluate_eligibility(
        _pensionado_payload(police_clearance_available="no"),
        pathway="costa-rica-pensionado",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["police_clearance_unavailable"]


def test_costa_rica_pensionado_foreign_pension_gap_returns_needs_review():
    result = evaluate_eligibility(
        _pensionado_payload(pension_foreign_source_confirmed="not_sure"),
        pathway="costa-rica-pensionado",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["foreign_pension_source_unconfirmed"]


def test_costa_rica_pensionado_pension_duration_gap_returns_needs_review():
    result = evaluate_eligibility(
        _pensionado_payload(pension_duration_type="fixed_term_less_than_12_months"),
        pathway="costa-rica-pensionado",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["pension_duration_needs_review"]


def test_costa_rica_pensionado_criminal_record_returns_needs_review():
    result = evaluate_eligibility(
        _pensionado_payload(criminal_record_flag="yes"),
        pathway="costa-rica-pensionado",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["criminal_record_needs_review"]


def test_costa_rica_pensionado_pension_receipt_gap_returns_needs_review():
    result = evaluate_eligibility(
        _pensionado_payload(pension_receipt_evidence="cannot_document"),
        pathway="costa-rica-pensionado",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "pension_receipt_costa_rica_evidence_unavailable"
    ]


def test_costa_rica_pensionado_output_uses_pathway_files():
    eligibility = evaluate_eligibility(
        _pensionado_payload(police_clearance_available="no"),
        pathway="costa-rica-pensionado",
    )
    output = build_output(eligibility)

    assert output["meta"]["visa_type"] == "Costa Rica Pensionado Residency"
    assert "manual review" in output["summary"].lower()
    assert output["next_steps"]["action"]["type"] == "email_followup"
    assert output["clarifications"][0]["requirement"] == "police_clearance_unavailable"


def test_costa_rica_pensionado_new_review_reasons_use_clarifications():
    eligibility = evaluate_eligibility(
        _pensionado_payload(pension_foreign_source_confirmed="no"),
        pathway="costa-rica-pensionado",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "foreign_pension_source_unconfirmed"
    assert "issued from outside Costa Rica" in output["clarifications"][0]["clarification"]


def test_spain_below_2800_returns_not_eligible():
    result = evaluate_eligibility(
        _spain_payload(income_band="below_2800"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["income_below_minimum"]


def test_spain_non_foreign_income_returns_not_eligible():
    result = evaluate_eligibility(
        _spain_payload(foreign_income="no"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["foreign_income_source_unconfirmed"]


def test_spain_short_income_history_returns_needs_review():
    result = evaluate_eligibility(
        _spain_payload(income_history="less_than_3"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["income_duration_needs_review"]


def test_spain_incomplete_income_evidence_returns_needs_review():
    result = evaluate_eligibility(
        _spain_payload(income_evidence_types=["bank_statements"]),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["income_evidence_incomplete"]


def test_spain_passport_background_and_insurance_gaps_return_needs_review():
    result = evaluate_eligibility(
        _spain_payload(
            passport_validity_months="6",
            police_clearance_available="no",
            criminal_record_flag="yes",
            health_insurance_status="not_ready",
        ),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "passport_validity_needs_review",
        "police_clearance_unavailable",
        "criminal_record_needs_review",
        "health_insurance_not_ready",
    ]


def test_spain_document_and_compliance_gaps_return_needs_review():
    result = evaluate_eligibility(
        _spain_payload(
            civil_documents_available="no",
            apostille_translation_ready="no",
            renewal_compliance_acknowledged="no",
        ),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "civil_documents_unavailable",
        "apostille_translation_not_ready",
        "renewal_compliance_acknowledgement_missing",
    ]


def test_spain_dependent_documents_gap_returns_needs_review():
    payload = _spain_payload(has_dependents="yes", dependents_count="1")
    payload["documents"]["dependent_documents_available"] = "no"

    result = evaluate_eligibility(payload, pathway="spain-dnv")

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["dependent_documents_unavailable"]


def test_spain_valid_dnv_applicant_returns_eligible():
    result = evaluate_eligibility(_spain_payload(), pathway="spain_dnv")

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["visa_type"] == "Spain Digital Nomad Visa"


def test_spain_contractor_without_service_agreements_returns_needs_review():
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="contractor",
            service_agreements="cannot_secure_service_agreements",
        ),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "contractor_service_agreements_unavailable"
    ]


def test_spain_tax_only_returns_needs_review():
    result = evaluate_eligibility(
        _spain_payload(service_interest="tax_services"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["non_dnv_service_interest"]


def test_spain_eligible_result_uses_spain_dnv_output():
    eligibility = evaluate_eligibility(_spain_payload(), pathway="spain-dnv")
    output = build_output(eligibility)

    assert output["meta"]["visa_type"] == "Spain Digital Nomad Visa"
    assert "Spain's Digital Nomad Visa" in output["summary"]
    assert output["next_steps"]["action"]["type"] == "consultation"
    assert output["next_steps"]["action"]["label"] == "Book a Spain DNV consultation"


def test_spain_needs_review_uses_email_output():
    eligibility = evaluate_eligibility(
        _spain_payload(
            work_relationship="contractor",
            service_agreements="cannot_secure_service_agreements",
        ),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["meta"]["status"] == "needs_review"
    assert "manual review" in output["summary"].lower()
    assert output["next_steps"]["action"]["type"] == "email_followup"


def test_spain_not_eligible_uses_not_qualified_output():
    eligibility = evaluate_eligibility(
        _spain_payload(income_band="below_2800"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["meta"]["status"] == "not_eligible"
    assert "do not currently appear to meet" in output["summary"]
    assert output["next_steps"]["action"]["type"] == "informational"


def test_spain_tax_only_uses_tax_follow_up_output():
    eligibility = evaluate_eligibility(
        _spain_payload(service_interest="tax_services"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["meta"]["status"] == "needs_review"
    assert "tax" in output["summary"].lower()
    assert output["next_steps"]["action"]["label"] == "Wait for tax-service follow-up"


def test_costa_rica_output_still_uses_default_taxonomy():
    eligibility = evaluate_eligibility(_complete_contractor_payload())
    output = build_output(eligibility)

    assert output["meta"]["visa_type"] == "Digital Nomad"
    assert output["summary"] == "Based on the information provided, you meet the eligibility requirements."
    assert output["next_steps"]["action"]["label"] == "Book a consultation with Great Expatations"


def test_spain_below_2800_includes_income_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(income_band="below_2800"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "income_below_minimum"
    assert "minimum qualifying band" in output["clarifications"][0]["clarification"]


def test_spain_foreign_income_failure_includes_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(foreign_income="no"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "foreign_income_source_unconfirmed"
    assert "earned from outside Spain" in output["clarifications"][0]["clarification"]


def test_spain_contractor_review_includes_service_agreement_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(
            work_relationship="contractor",
            service_agreements="cannot_secure_service_agreements",
        ),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "contractor_service_agreements_unavailable"
    assert "business-to-business work relationships" in output["clarifications"][0]["clarification"]


def test_spain_tax_only_includes_non_dnv_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(service_interest="tax_services"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "non_dnv_service_interest"
    assert "tax or advisory follow-up" in output["clarifications"][0]["clarification"]


def test_spain_manual_review_includes_manual_review_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(income_band="unrecognized_band"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["meta"]["status"] == "needs_review"
    assert output["clarifications"][0]["requirement"] == "income_band_missing_or_unrecognized"
    assert "reviewed manually" in output["clarifications"][0]["clarification"]


def test_spain_generic_manual_review_clarification_is_available():
    output = build_output(
        {
            "eligibility_status": "needs_review",
            "failed_requirements": ["needs_manual_review"],
            "routing": {},
            "work_type": "employee",
            "visa_type": "Spain Digital Nomad Visa",
        }
    )

    assert output["clarifications"][0]["requirement"] == "needs_manual_review"
    assert "not enough to confirm Spain DNV eligibility automatically" in output["clarifications"][0]["clarification"]


def test_spain_aliases_load_first_question():
    result_dash = evaluate({}, pathway="spain-dnv")
    result_underscore = evaluate({}, pathway="spain_dnv")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "routing.service_interest"
    assert result_dash["field"]["input_type"] == "multi_choice"
    assert result_dash["field"]["choices"] == ["digital_nomad_visa", "tax_services"]


def test_spain_dnv_skips_costa_rica_applicant_type_gate():
    payload = {"routing": {"service_interest": "digital_nomad_visa"}}
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "routing.work_relationship"
    assert result["field"]["choices"] == ["business_owner", "contractor", "employee"]


def test_spain_contractor_question_loads_conditionally():
    payload = {
        "routing": {
            "service_interest": "digital_nomad_visa",
            "work_relationship": "contractor",
        }
    }
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "role.contractor.service_agreements_available"
    assert result["field"]["choices"] == [
        "can_secure_service_agreements",
        "cannot_secure_service_agreements",
    ]


def test_spain_non_contractor_skips_contractor_question():
    payload = {
        "routing": {
            "service_interest": "digital_nomad_visa",
            "work_relationship": "employee",
        }
    }
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "role.profession_description"


def test_spain_tax_only_routes_to_contact_fields():
    payload = {"routing": {"service_interest": "tax_services"}}
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "identity.first_name"
