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

    assert result["next_field_key"] == "routing.work_relationship"
    assert result["field"]["choices"] == ["business_owner", "contractor", "employee"]


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
    work_relationship="employee",
    monthly_income_eur="2800",
    income_history="12_or_more",
    income_evidence_types=None,
    passport_validity_months="24",
    police_clearance_available="yes",
    criminal_record_flag="no",
    health_insurance_status="will_obtain",
    applicant_type="individual",
    dependents_count=None,
    service_agreements=None,
    employer_outside_spain="yes",
    foreign_employment_months="12",
    remote_work_approved="yes",
    foreign_client_relationship="yes",
    foreign_client_relationship_months="12",
    spanish_clients_flag="no",
    spanish_activity_percentage=None,
    supporting_company_operating_1_year="yes",
    business_owner_work_structure="salary_as_employee",
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
            "work_relationship": work_relationship,
            "passport_validity_months": passport_validity_months,
            "criminal_record_flag": criminal_record_flag,
            "health_insurance_status": health_insurance_status,
            "applicant_type": applicant_type,
        },
        "identity": {
            "nationality": "United States",
        },
        "documents": {
            "police_clearance_available": police_clearance_available,
        },
        "role": {},
    }
    if applicant_type == "family":
        payload["routing"]["dependents_count"] = (
            "1" if dependents_count is None else dependents_count
        )

    if work_relationship in ("employee", "contractor", "business_owner"):
        payload["routing"]["supporting_company_operating_1_year"] = (
            supporting_company_operating_1_year
        )

    if service_agreements is not None:
        payload["role"]["contractor"] = {
            "service_agreements_available": service_agreements,
        }
    elif work_relationship == "contractor":
        payload["role"]["contractor"] = {
            "service_agreements_available": "can_secure_service_agreements",
        }

    role_payload = payload["role"].setdefault(work_relationship, {})
    role_payload.update(
        {
            "monthly_income_eur": monthly_income_eur,
            "income_evidence_months": income_history,
            "income_evidence_types": income_evidence_types,
        }
    )

    if work_relationship == "employee":
        role_payload.update(
            {
                "employer_outside_spain": employer_outside_spain,
                "foreign_employment_months": foreign_employment_months,
                "remote_work_approved": remote_work_approved,
            }
        )

    if work_relationship == "contractor":
        role_payload.update(
            {
                "foreign_client_relationship": foreign_client_relationship,
                "foreign_client_relationship_months": foreign_client_relationship_months,
                "spanish_clients_flag": spanish_clients_flag,
            }
        )
        if spanish_activity_percentage is not None:
            role_payload["spanish_activity_percentage"] = spanish_activity_percentage

    if work_relationship == "business_owner":
        role_payload["work_structure"] = business_owner_work_structure
        if business_owner_work_structure == "salary_as_employee":
            role_payload.update(
                {
                    "employer_outside_spain": employer_outside_spain,
                    "foreign_employment_months": foreign_employment_months,
                    "remote_work_approved": remote_work_approved,
                }
            )
        elif business_owner_work_structure == "business_or_self_employment_income":
            role_payload.update(
                {
                    "foreign_client_relationship": foreign_client_relationship,
                    "foreign_client_relationship_months": foreign_client_relationship_months,
                    "spanish_clients_flag": spanish_clients_flag,
                }
            )
            if spanish_activity_percentage is not None:
                role_payload["spanish_activity_percentage"] = spanish_activity_percentage

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
        _spain_payload(monthly_income_eur="2799"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["income_below_minimum"]


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
    assert result["failed_requirements"] == ["employee_income_evidence_incomplete"]


def test_spain_each_work_type_gets_only_its_role_income_fields():
    cases = {
        "employee": [
            "role.employee.employer_outside_spain",
            "role.employee.foreign_employment_months",
            "role.employee.remote_work_approved",
            "role.employee.monthly_income_eur",
            "role.employee.income_evidence_types",
            "role.employee.income_evidence_months",
            "routing.supporting_company_operating_1_year",
        ],
        "contractor": [
            "role.contractor.foreign_client_relationship",
            "role.contractor.foreign_client_relationship_months",
            "role.contractor.spanish_clients_flag",
            "role.contractor.service_agreements_available",
            "role.contractor.monthly_income_eur",
            "role.contractor.income_evidence_types",
            "role.contractor.income_evidence_months",
            "routing.supporting_company_operating_1_year",
        ],
        "business_owner": [
            "role.business_owner.work_structure",
            "role.business_owner.employer_outside_spain",
            "role.business_owner.foreign_employment_months",
            "role.business_owner.remote_work_approved",
            "role.business_owner.monthly_income_eur",
            "role.business_owner.income_evidence_types",
            "role.business_owner.income_evidence_months",
            "routing.supporting_company_operating_1_year",
        ],
    }
    answers = {
        "role.employee.employer_outside_spain": "yes",
        "role.employee.foreign_employment_months": "12",
        "role.employee.remote_work_approved": "yes",
        "role.employee.monthly_income_eur": "2800",
        "role.employee.income_evidence_types": [
            "bank_statements",
            "employment_contract",
            "pay_stubs",
        ],
        "role.employee.income_evidence_months": "12_or_more",
        "role.contractor.foreign_client_relationship": "yes",
        "role.contractor.foreign_client_relationship_months": "12",
        "role.contractor.spanish_clients_flag": "no",
        "role.contractor.service_agreements_available": "can_secure_service_agreements",
        "role.contractor.monthly_income_eur": "2800",
        "role.contractor.income_evidence_types": [
            "bank_statements",
            "service_agreements_or_contracts",
            "invoices",
        ],
        "role.contractor.income_evidence_months": "12_or_more",
        "routing.supporting_company_operating_1_year": "yes",
        "role.business_owner.work_structure": "salary_as_employee",
        "role.business_owner.employer_outside_spain": "yes",
        "role.business_owner.foreign_employment_months": "12",
        "role.business_owner.remote_work_approved": "yes",
        "role.business_owner.monthly_income_eur": "2800",
        "role.business_owner.income_evidence_types": [
            "bank_statements",
            "business_registration",
            "tax_returns_or_financial_statements",
        ],
        "role.business_owner.income_evidence_months": "12_or_more",
    }

    for work_relationship, expected_keys in cases.items():
        payload = {"routing": {"work_relationship": work_relationship}, "role": {}}

        asked_keys = []
        for expected_key in expected_keys:
            result = evaluate(payload, pathway="spain-dnv")
            asked_keys.append(result["next_field_key"])
            assert result["next_field_key"] == expected_key

            current = payload
            parts = expected_key.split(".")
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = answers[expected_key]

        result = evaluate(payload, pathway="spain-dnv")
        assert result["next_field_key"] == "routing.applicant_type"
        assert all("income." not in key for key in asked_keys)


def test_spain_valid_employee_contractor_and_business_owner_can_return_eligible():
    for work_relationship in ("employee", "contractor", "business_owner"):
        result = evaluate_eligibility(
            _spain_payload(work_relationship=work_relationship),
            pathway="spain-dnv",
        )

        assert result["eligibility_status"] == "eligible"
        assert result["failed_requirements"] == []


def test_spain_business_owner_salary_as_employee_reuses_employee_style_checks():
    # Passing case.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="salary_as_employee",
            employer_outside_spain="yes",
            foreign_employment_months="12",
            remote_work_approved="yes",
            supporting_company_operating_1_year="yes",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []

    # Employer/company based in Spain -> reuses the employee hard failure code.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="salary_as_employee",
            employer_outside_spain="no",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert "employee_employer_located_in_spain" in result["failed_requirements"]

    # Relationship below 3 months.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="salary_as_employee",
            foreign_employment_months="2",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "employee_foreign_employment_duration_below_minimum"
        in result["failed_requirements"]
    )

    # Remote work not approved.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="salary_as_employee",
            remote_work_approved="no",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert "employee_remote_work_not_approved" in result["failed_requirements"]

    # Supporting company operating history below 1 year.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="salary_as_employee",
            supporting_company_operating_1_year="no",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "supporting_company_operating_history_below_minimum"
        in result["failed_requirements"]
    )


def test_spain_business_owner_self_employment_reuses_contractor_style_checks():
    # Passing case.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="business_or_self_employment_income",
            foreign_client_relationship="yes",
            foreign_client_relationship_months="12",
            spanish_clients_flag="no",
            supporting_company_operating_1_year="yes",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []

    # No qualifying foreign client/company relationship.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="business_or_self_employment_income",
            foreign_client_relationship="no",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "contractor_foreign_client_relationship_missing"
        in result["failed_requirements"]
    )

    # Relationship below 3 months.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="business_or_self_employment_income",
            foreign_client_relationship_months="2",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "contractor_foreign_client_duration_below_minimum"
        in result["failed_requirements"]
    )

    # Spain-based activity at or below the 20% allowance is fine.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="business_or_self_employment_income",
            spanish_clients_flag="yes",
            spanish_activity_percentage="20",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []

    # Spain-based activity above the 20% allowance fails.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="business_or_self_employment_income",
            spanish_clients_flag="yes",
            spanish_activity_percentage="21",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "contractor_spanish_activity_above_threshold" in result["failed_requirements"]
    )

    # Supporting company operating history below 1 year.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_owner_work_structure="business_or_self_employment_income",
            supporting_company_operating_1_year="no",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "supporting_company_operating_history_below_minimum"
        in result["failed_requirements"]
    )


def test_spain_business_owner_missing_work_structure_returns_needs_review():
    payload = _spain_payload(work_relationship="business_owner")
    del payload["role"]["business_owner"]["work_structure"]

    result = evaluate_eligibility(payload, pathway="spain-dnv")

    assert result["eligibility_status"] == "needs_review"
    assert "business_owner_work_structure_needs_review" in result["failed_requirements"]


def test_spain_business_owner_question_order_by_work_structure():
    salary_payload = {"routing": {"work_relationship": "business_owner"}, "role": {}}
    result = evaluate(salary_payload, pathway="spain-dnv")
    assert result["next_field_key"] == "role.business_owner.work_structure"

    salary_payload["role"]["business_owner"] = {"work_structure": "salary_as_employee"}
    result = evaluate(salary_payload, pathway="spain-dnv")
    assert result["next_field_key"] == "role.business_owner.employer_outside_spain"

    self_employment_payload = {
        "routing": {"work_relationship": "business_owner"},
        "role": {
            "business_owner": {
                "work_structure": "business_or_self_employment_income",
            }
        },
    }
    result = evaluate(self_employment_payload, pathway="spain-dnv")
    assert result["next_field_key"] == "role.business_owner.foreign_client_relationship"


def test_spain_no_escape_choices_in_business_owner_questions():
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


def test_spain_role_specific_evidence_gaps_return_needs_review():
    cases = {
        "employee": "employee_income_evidence_incomplete",
        "contractor": "contractor_income_evidence_incomplete",
        "business_owner": "business_owner_income_evidence_incomplete",
    }

    for work_relationship, expected_failure in cases.items():
        result = evaluate_eligibility(
            _spain_payload(
                work_relationship=work_relationship,
                income_evidence_types=["bank_statements"],
            ),
            pathway="spain-dnv",
        )

        assert result["eligibility_status"] == "needs_review"
        assert result["failed_requirements"] == [expected_failure]


def test_spain_role_specific_evidence_failure_uses_role_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            income_evidence_types=["bank_statements"],
        ),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == (
        "business_owner_income_evidence_incomplete"
    )
    assert "Business-owner applicants" in output["clarifications"][0]["clarification"]


def test_spain_passport_background_and_insurance_gaps_return_needs_review():
    result = evaluate_eligibility(
        _spain_payload(
            passport_validity_months="6",
            police_clearance_available="no",
            criminal_record_flag="yes",
            health_insurance_status="unknown",
        ),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "passport_validity_needs_review",
        "health_insurance_not_ready",
        "police_clearance_unavailable",
        "criminal_record_needs_review",
    ]


def test_spain_family_without_dependent_count_returns_needs_review():
    result = evaluate_eligibility(
        _spain_payload(applicant_type="family", dependents_count=""),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["dependents_count_missing"]


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
        _spain_payload(monthly_income_eur="2799"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["meta"]["status"] == "not_eligible"
    assert "do not currently appear to meet" in output["summary"]
    assert output["next_steps"]["action"]["type"] == "informational"


def test_costa_rica_output_still_uses_default_taxonomy():
    eligibility = evaluate_eligibility(_complete_contractor_payload())
    output = build_output(eligibility)

    assert output["meta"]["visa_type"] == "Digital Nomad"
    assert output["summary"] == "Based on the information provided, you meet the eligibility requirements."
    assert output["next_steps"]["action"]["label"] == "Book a consultation with Great Expatations"


def test_spain_below_2800_includes_income_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(monthly_income_eur="2799"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "income_below_minimum"
    assert "EUR 2,800" in output["clarifications"][0]["clarification"]


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


def test_spain_manual_review_includes_manual_review_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(monthly_income_eur="not-a-number"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["meta"]["status"] == "needs_review"
    assert output["clarifications"][0]["requirement"] == "income_amount_missing_or_unrecognized"
    assert "numeric EUR amount" in output["clarifications"][0]["clarification"]


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
    assert result_dash["next_field_key"] == "routing.work_relationship"
    assert result_dash["field"]["input_type"] == "choice"
    assert result_dash["field"]["choices"] == ["business_owner", "contractor", "employee"]


def test_spain_no_longer_asks_service_interest_or_profession():
    payload = {"routing": {"work_relationship": "employee"}}
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "role.employee.employer_outside_spain"
    assert result["next_field_key"] != "routing.service_interest"
    assert result["next_field_key"] != "role.profession_description"


def test_spain_numeric_income_question_has_no_band_choices():
    result = evaluate(
        {
            "routing": {"work_relationship": "employee"},
            "role": {
                "employee": {
                    "employer_outside_spain": "yes",
                    "foreign_employment_months": "12",
                    "remote_work_approved": "yes",
                }
            },
        },
        pathway="spain-dnv",
    )

    assert result["next_field_key"] == "role.employee.monthly_income_eur"
    assert result["field"]["input_type"] == "number"
    assert "choices" not in result["field"]


def test_spain_dependent_question_uses_individual_family_choices():
    payload = _spain_payload()
    payload["routing"].pop("applicant_type")

    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "routing.applicant_type"
    assert result["field"]["choices"] == ["individual", "family"]


def test_spain_no_longer_asks_document_readiness_questions():
    payload = _spain_payload()
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] is None
    assert "documents.dependent_documents_available" not in result["missing_fields"]
    assert "documents.civil_documents_available" not in result["missing_fields"]
    assert "documents.apostille_translation_ready" not in result["missing_fields"]
    assert "routing.renewal_compliance_acknowledged" not in result["missing_fields"]
