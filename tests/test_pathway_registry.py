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
    assert resolve_pathway("spain-nlv").canonical_id == "spain_nlv"
    assert resolve_pathway("spain_nlv").canonical_id == "spain_nlv"
    assert resolve_pathway("spain-student-visa").canonical_id == "spain_student_visa"
    assert resolve_pathway("spain_student_visa").canonical_id == "spain_student_visa"
    assert (
        resolve_pathway("italy-elective-residence").canonical_id
        == "italy_elective_residence"
    )
    assert (
        resolve_pathway("italy_elective_residence").canonical_id
        == "italy_elective_residence"
    )
    assert resolve_pathway("portugal-d7").canonical_id == "portugal_d7"
    assert resolve_pathway("portugal_d7").canonical_id == "portugal_d7"
    assert resolve_pathway("portugal-dnv").canonical_id == "portugal_dnv"
    assert resolve_pathway("portugal_dnv").canonical_id == "portugal_dnv"
    assert resolve_pathway("portugal-digital-nomad").canonical_id == "portugal_dnv"
    assert (
        resolve_pathway("portugal-digital-nomad-visa").canonical_id
        == "portugal_dnv"
    )
    assert resolve_pathway("portugal-remote-work").canonical_id == "portugal_dnv"
    assert (
        resolve_pathway("portugal-remote-work-visa").canonical_id
        == "portugal_dnv"
    )
    assert (
        resolve_pathway("portugal-golden-visa").canonical_id
        == "portugal_golden_visa"
    )
    assert (
        resolve_pathway("portugal_golden_visa").canonical_id
        == "portugal_golden_visa"
    )
    assert resolve_pathway("portugal-ari").canonical_id == "portugal_golden_visa"
    assert resolve_pathway("portugal_ari").canonical_id == "portugal_golden_visa"
    assert (
        resolve_pathway("portugal-investment-residence").canonical_id
        == "portugal_golden_visa"
    )
    assert (
        resolve_pathway("portugal-investment-residence-permit").canonical_id
        == "portugal_golden_visa"
    )
    assert resolve_pathway("costa-rica-pensionado").canonical_id == "costa_rica_pensionado"
    assert resolve_pathway("costa_rica_pensionado").canonical_id == "costa_rica_pensionado"
    assert resolve_pathway("spain-dnv").implemented is False
    assert resolve_pathway("spain-dnv").questions_file == "pathways/spain_dnv/questions.json"
    assert resolve_pathway("spain-nlv").implemented is True
    assert resolve_pathway("spain-nlv").questions_file == "pathways/spain_nlv/questions.json"
    assert (
        resolve_pathway("spain-nlv").rules_module
        == "app.engine.pathways.spain_nlv.rules"
    )
    assert resolve_pathway("spain-nlv").output_file == "pathways/spain_nlv/output.json"
    assert (
        resolve_pathway("spain-nlv").clarifications_file
        == "pathways/spain_nlv/clarifications.json"
    )
    assert resolve_pathway("spain-student-visa").implemented is True
    assert (
        resolve_pathway("spain-student-visa").questions_file
        == "pathways/spain_student_visa/questions.json"
    )
    assert (
        resolve_pathway("spain-student-visa").rules_module
        == "app.engine.pathways.spain_student_visa.rules"
    )
    assert (
        resolve_pathway("spain-student-visa").output_file
        == "pathways/spain_student_visa/output.json"
    )
    assert (
        resolve_pathway("spain-student-visa").clarifications_file
        == "pathways/spain_student_visa/clarifications.json"
    )
    assert resolve_pathway("italy-elective-residence").implemented is True
    assert (
        resolve_pathway("italy-elective-residence").questions_file
        == "pathways/italy_elective_residence/questions.json"
    )
    assert (
        resolve_pathway("italy-elective-residence").rules_module
        == "app.engine.pathways.italy_elective_residence.rules"
    )
    assert (
        resolve_pathway("italy-elective-residence").output_file
        == "pathways/italy_elective_residence/output.json"
    )
    assert (
        resolve_pathway("italy-elective-residence").clarifications_file
        == "pathways/italy_elective_residence/clarifications.json"
    )
    assert resolve_pathway("portugal-d7").implemented is True
    assert (
        resolve_pathway("portugal-d7").questions_file
        == "pathways/portugal_d7/questions.json"
    )
    assert (
        resolve_pathway("portugal-d7").rules_module
        == "app.engine.pathways.portugal_d7.rules"
    )
    assert resolve_pathway("portugal-d7").output_file == "pathways/portugal_d7/output.json"
    assert (
        resolve_pathway("portugal-d7").clarifications_file
        == "pathways/portugal_d7/clarifications.json"
    )
    assert resolve_pathway("portugal-dnv").implemented is True
    assert (
        resolve_pathway("portugal-dnv").questions_file
        == "pathways/portugal_dnv/questions.json"
    )
    assert (
        resolve_pathway("portugal-dnv").rules_module
        == "app.engine.pathways.portugal_dnv.rules"
    )
    assert (
        resolve_pathway("portugal-dnv").output_file
        == "pathways/portugal_dnv/output.json"
    )
    assert (
        resolve_pathway("portugal-dnv").clarifications_file
        == "pathways/portugal_dnv/clarifications.json"
    )
    assert resolve_pathway("portugal-golden-visa").implemented is True
    assert (
        resolve_pathway("portugal-golden-visa").questions_file
        == "pathways/portugal_golden_visa/questions.json"
    )
    assert (
        resolve_pathway("portugal-golden-visa").rules_module
        == "app.engine.pathways.portugal_golden_visa.rules"
    )
    assert (
        resolve_pathway("portugal-golden-visa").output_file
        == "pathways/portugal_golden_visa/output.json"
    )
    assert (
        resolve_pathway("portugal-golden-visa").clarifications_file
        == "pathways/portugal_golden_visa/clarifications.json"
    )
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
    assert result["field"]["choices"] == [
        "spain_dnv",
        "spain_nlv",
        "spain_student_visa",
    ]


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
    employer_outside_spain="yes",
    foreign_employment_months="12",
    remote_work_approved="yes",
    employer_company_operating_1_year="yes",
    qualification_or_experience="qualifying_education",
    foreign_client_relationship="yes",
    foreign_client_relationship_months="12",
    remote_work_capable="yes",
    foreign_company_operating_1_year="yes",
    spanish_clients_flag="no",
    spanish_activity_percentage=None,
    business_outside_spain="yes",
    months_owned_operated="12",
    remote_operation_capable="yes",
    business_operating_1_year="yes",
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
                "employer_company_operating_1_year": employer_company_operating_1_year,
                "qualification_or_experience": qualification_or_experience,
            }
        )

    if work_relationship == "contractor":
        role_payload.update(
            {
                "foreign_client_relationship": foreign_client_relationship,
                "foreign_client_relationship_months": foreign_client_relationship_months,
                "remote_work_capable": remote_work_capable,
                "foreign_company_operating_1_year": foreign_company_operating_1_year,
                "qualification_or_experience": qualification_or_experience,
                "spanish_clients_flag": spanish_clients_flag,
            }
        )
        if spanish_activity_percentage is not None:
            role_payload["spanish_activity_percentage"] = spanish_activity_percentage

    if work_relationship == "business_owner":
        role_payload.update(
            {
                "business_outside_spain": business_outside_spain,
                "months_owned_operated": months_owned_operated,
                "remote_operation_capable": remote_operation_capable,
                "business_operating_1_year": business_operating_1_year,
                "qualification_or_experience": qualification_or_experience,
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
    intends_to_work_in_costa_rica="no",
):
    return {
        "routing": {
            "applicant_type": "individual",
            "passport_validity_months": "24",
            "criminal_record_flag": criminal_record_flag,
        },
        "identity": {
            "nationality": "United States",
            "country_of_residence": "United States",
        },
        "work": {
            "intends_to_work_in_costa_rica": intends_to_work_in_costa_rica,
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


def _spain_nlv_payload(
    *,
    applicant_type="individual",
    eu_eea_swiss_citizen="no",
    eu_family_member_route="no",
    intends_to_work_in_spain="no",
    monthly_financial_means="2400",
    dependents_count=None,
    minor_children_schooling_status="can_enroll",
    spanish_company_ownership="no",
    performs_labor_for_spanish_company=None,
    health_insurance_status="have_it",
    background_check_available="yes",
    criminal_record_flag="no",
    public_order_security_risk_flag="no",
    public_health_disease_flag="no",
):
    payload = {
        "routing": {
            "applicant_type": applicant_type,
            "irregular_presence_spain": "no",
            "passport_validity_months": "24",
            "health_insurance_status": health_insurance_status,
            "background_check_available": background_check_available,
            "criminal_record_flag": criminal_record_flag,
            "public_order_security_risk_flag": public_order_security_risk_flag,
            "public_health_disease_flag": public_health_disease_flag,
        },
        "identity": {
            "nationality": "United States",
            "eu_eea_swiss_citizen": eu_eea_swiss_citizen,
        },
        "work": {
            "intends_to_work_in_spain": intends_to_work_in_spain,
        },
        "financial": {
            "monthly_passive_income_or_assets_eur": monthly_financial_means,
            "funds_evidence_types": ["bank_certificates"],
            "spanish_company_ownership": spanish_company_ownership,
        },
    }

    if eu_eea_swiss_citizen == "no":
        payload["identity"]["eu_family_member_route"] = eu_family_member_route

    if applicant_type == "family":
        payload["routing"].update(
            {
                "dependents_count": "1" if dependents_count is None else dependents_count,
                "dependent_relationships": "spouse, child",
                "dependent_ages": "38, 9",
                "minor_children_schooling_status": minor_children_schooling_status,
            }
        )

    if performs_labor_for_spanish_company is not None:
        payload["financial"][
            "performs_labor_for_spanish_company"
        ] = performs_labor_for_spanish_company

    return payload


def _italy_elective_residence_payload(
    *,
    applicant_type="individual",
    annual_passive_income_eur="50000",
    available_assets_eur="250000",
    intends_to_work_in_italy="no",
    italy_lodging_status="registered_lease",
    dependents_count=None,
    family_documents_available="yes",
):
    payload = {
        "routing": {
            "applicant_type": applicant_type,
            "consulate_jurisdiction": "new_york",
            "stable_residence_intent": "stable_residence",
            "health_insurance_status": "have_it",
            "health_insurance_coverage_level": "meets_consular_coverage",
            "passport_validity_months": "24",
            "passport_issued_within_10_years": "yes",
            "passport_blank_pages": "2",
        },
        "identity": {
            "nationality": "United States",
        },
        "work": {
            "intends_to_work_in_italy": intends_to_work_in_italy,
        },
        "financial": {
            "annual_passive_income_eur": annual_passive_income_eur,
            "available_assets_eur": available_assets_eur,
            "income_source_types": ["pension"],
            "income_evidence_types": ["bank_letters"],
            "tax_returns_available": "two_years_complete_with_schedules",
        },
        "housing": {
            "italy_lodging_status": italy_lodging_status,
        },
        "compliance": {
            "permesso_8_day_acknowledged": "yes",
            "annual_renewal_acknowledged": "yes",
        },
    }

    if applicant_type == "family":
        payload["routing"].update(
            {
                "dependents_count": "1" if dependents_count is None else dependents_count,
                "dependent_relationships": "spouse",
                "dependent_adult_children_living_with_parents": "no_adult_children",
                "family_documents_available": family_documents_available,
            }
        )

    return payload


def _portugal_d7_payload(
    *,
    applicant_type="individual",
    annual_passive_income_eur="20000",
    application_country_matches_nationality="yes",
    lawful_residence_where_applying=None,
    passive_own_income_intent="yes",
    portuguese_bank_availability="yes",
    portugal_accommodation_12_months="lease_12_months_or_more",
    police_clearance_available="yes",
    criminal_record_flag="no",
    dependents_count=None,
    additional_adult_dependents_count=None,
    child_or_dependent_non_minor_count=None,
):
    payload = {
        "routing": {
            "applicant_type": applicant_type,
            "application_country_matches_nationality": application_country_matches_nationality,
            "passive_own_income_intent": passive_own_income_intent,
            "passport_validity_months": "12",
            "health_travel_insurance_status": "have_it",
            "police_clearance_available": police_clearance_available,
            "criminal_record_flag": criminal_record_flag,
        },
        "identity": {
            "nationality": "United States",
        },
        "financial": {
            "annual_passive_income_eur": annual_passive_income_eur,
            "income_source_types": ["pension"],
            "income_evidence_types": ["bank_statements"],
            "portuguese_bank_availability": portuguese_bank_availability,
        },
        "housing": {
            "portugal_accommodation_12_months": portugal_accommodation_12_months,
        },
        "compliance": {
            "truthful_documents_acknowledged": "yes",
        },
    }

    if lawful_residence_where_applying is not None:
        payload["routing"][
            "lawful_residence_where_applying"
        ] = lawful_residence_where_applying

    if applicant_type == "family":
        payload["routing"].update(
            {
                "dependents_count": (
                    "2" if dependents_count is None else dependents_count
                ),
                "additional_adult_dependents_count": (
                    "1"
                    if additional_adult_dependents_count is None
                    else additional_adult_dependents_count
                ),
                "child_or_dependent_non_minor_count": (
                    "1"
                    if child_or_dependent_non_minor_count is None
                    else child_or_dependent_non_minor_count
                ),
                "dependent_relationships": "spouse, child",
                "family_documents_available": "yes",
            }
        )

    return payload


def _portugal_dnv_payload(
    *,
    visa_route="residence_visa",
    work_relationship="remote_employee",
    average_monthly_income_last_3_months_eur="3680",
    entities_outside_portugal="yes",
    employee_contract_or_declaration_available="yes",
    independent_service_or_client_proof_available="yes",
    business_owner_company_service_documents_available="yes",
    tax_residence_certificate_available="yes",
    applicant_type="individual",
    family_documents_available="yes",
    family_stable_means_available="yes",
):
    payload = {
        "routing": {
            "visa_route": visa_route,
            "work_relationship": work_relationship,
            "applicant_type": applicant_type,
            "application_country_matches_nationality": "yes",
            "passport_validity_months": "12",
            "health_travel_insurance_status": "have_it",
            "police_clearance_available": "yes",
            "criminal_record_flag": "no",
            "removal_or_refusal_alert_flag": "no",
        },
        "identity": {
            "nationality": "United States",
        },
        "work": {
            "entities_outside_portugal": entities_outside_portugal,
        },
        "role": {
            "employee": {
                "contract_or_declaration_available": (
                    employee_contract_or_declaration_available
                ),
            },
            "independent": {
                "service_or_client_proof_available": (
                    independent_service_or_client_proof_available
                ),
            },
            "business_owner": {
                "company_service_documents_available": (
                    business_owner_company_service_documents_available
                ),
            },
        },
        "financial": {
            "average_monthly_income_last_3_months_eur": (
                average_monthly_income_last_3_months_eur
            ),
            "income_evidence_types": ["bank_statements", "contracts"],
        },
        "documents": {
            "tax_residence_certificate_available": tax_residence_certificate_available,
        },
        "housing": {
            "settlement_statement_ready": "yes",
        },
        "compliance": {
            "truthful_documents_acknowledged": "yes",
        },
    }

    if applicant_type == "family":
        payload["routing"].update(
            {
                "dependents_count": "2",
                "dependent_relationships": "spouse, child",
                "family_documents_available": family_documents_available,
            }
        )
        payload["financial"][
            "family_stable_means_available"
        ] = family_stable_means_available

    return payload


def _portugal_golden_visa_payload(
    *,
    investment_route="job_creation",
    third_country_national_status="third_country_national",
    real_estate_only_basis="no",
    jobs_created_count="10",
    job_creation_evidence_available="yes",
    scientific_research_amount_eur="500000",
    scientific_research_confirmation_available="yes",
    arts_cultural_heritage_amount_eur="250000",
    arts_cultural_heritage_confirmation_available="yes",
    fund_amount_eur="500000",
    fund_non_real_estate_confirmed="yes",
    fund_maturity_confirmed="yes",
    fund_subscription_documents_available="yes",
    company_capitalization_amount_eur="500000",
    company_capitalization_job_plan="create_5_permanent_jobs",
    company_documents_available="yes",
    proof_of_funds_or_transfer_available="yes",
    applicant_type="individual",
    family_documents_available="yes",
    valid_passport_available="yes",
    criminal_record_certificate_available="yes_recent_translated_apostilled",
    serious_criminal_conviction_flag="no",
    entry_stay_ban_flag="no",
    sii_ucfe_refusal_alert_flag="no",
    portuguese_tax_clearance_status="debt_clearance_certificate",
    social_security_clearance_status="debt_clearance_certificate",
    foreign_tax_id_disclosure_available="yes",
    investment_maintenance_declaration_available="yes",
):
    payload = {
        "identity": {
            "nationality": "United States",
            "third_country_national_status": third_country_national_status,
        },
        "investment": {
            "route": investment_route,
            "real_estate_only_basis": real_estate_only_basis,
            "proof_of_funds_or_transfer_available": proof_of_funds_or_transfer_available,
            "job_creation": {
                "jobs_created_count": jobs_created_count,
                "evidence_available": job_creation_evidence_available,
            },
            "scientific_research": {
                "amount_eur": scientific_research_amount_eur,
                "institution_confirmation_available": (
                    scientific_research_confirmation_available
                ),
            },
            "arts_cultural_heritage": {
                "amount_eur": arts_cultural_heritage_amount_eur,
                "qualifying_entity_confirmation_available": (
                    arts_cultural_heritage_confirmation_available
                ),
            },
            "fund": {
                "amount_eur": fund_amount_eur,
                "non_real_estate_confirmed": fund_non_real_estate_confirmed,
                "maturity_and_portuguese_company_investment_confirmed": (
                    fund_maturity_confirmed
                ),
                "subscription_documents_available": (
                    fund_subscription_documents_available
                ),
            },
            "company_capitalization": {
                "amount_eur": company_capitalization_amount_eur,
                "jobs_requirement_plan": company_capitalization_job_plan,
                "company_and_employment_documents_available": (
                    company_documents_available
                ),
            },
        },
        "routing": {
            "applicant_type": applicant_type,
            "serious_criminal_conviction_flag": serious_criminal_conviction_flag,
            "entry_stay_ban_flag": entry_stay_ban_flag,
            "sii_ucfe_refusal_alert_flag": sii_ucfe_refusal_alert_flag,
        },
        "documents": {
            "valid_passport_available": valid_passport_available,
            "criminal_record_certificate_available": (
                criminal_record_certificate_available
            ),
            "portuguese_tax_clearance_status": portuguese_tax_clearance_status,
            "social_security_clearance_status": social_security_clearance_status,
            "foreign_tax_id_disclosure_available": foreign_tax_id_disclosure_available,
        },
        "compliance": {
            "investment_maintenance_declaration_available": (
                investment_maintenance_declaration_available
            ),
        },
    }

    if applicant_type == "family":
        payload["routing"].update(
            {
                "dependents_count": "2",
                "dependent_relationships": "spouse, child",
                "family_documents_available": family_documents_available,
            }
        )

    return payload


def _spain_student_payload(
    *,
    applicant_type="individual",
    monthly_funds_eur="600",
    dependents_count=None,
    stay_over_6_months="yes",
    background_check_available="yes",
    criminal_record_flag="no",
    study_category="higher_studies",
    student_work_intent="no_work",
):
    payload = {
        "routing": {
            "applicant_type": applicant_type,
            "irregular_presence_spain": "no",
            "application_route": "consular_outside_spain",
            "passport_validity_months": "24",
            "health_insurance_status": "have_it",
            "public_order_security_risk_flag": "no",
            "public_health_disease_flag": "no",
        },
        "identity": {
            "nationality": "United States",
            "eu_eea_swiss_or_free_movement_status": "no",
        },
        "study": {
            "category": study_category,
            "accepted_by_authorized_institution": "yes",
            "full_time_recognized_program": "yes",
            "modality": "hybrid",
            "in_person_requirement_met": "yes",
            "program_duration_months": "12",
            "stay_over_6_months": stay_over_6_months,
            "application_timing_status": "at_least_2_months_before_start",
            "enrollment_payment_status": "paid_or_proven",
            "student_work_intent": student_work_intent,
        },
        "financial": {
            "monthly_funds_eur": monthly_funds_eur,
            "accommodation_prepaid_full_stay": "no",
            "funds_evidence_types": ["bank_statements"],
        },
    }

    if stay_over_6_months == "yes":
        payload["identity"]["criminal_age_status"] = "yes"
        payload["routing"]["background_check_available"] = background_check_available
        payload["routing"]["criminal_record_flag"] = criminal_record_flag

    if applicant_type == "family":
        payload["routing"].update(
            {
                "dependents_count": "1" if dependents_count is None else dependents_count,
                "dependent_relationships": "spouse, child",
                "dependent_ages": "35, 8",
                "minor_children_included": "yes",
                "dependents_allowed_for_study_category": "yes",
                "dependents_work_intent": "no_work",
            }
        )

    return payload


def test_spain_student_visa_aliases_load_first_question():
    result_dash = evaluate({}, pathway="spain-student-visa")
    result_underscore = evaluate({}, pathway="spain_student_visa")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "routing.applicant_type"
    assert result_dash["field"]["input_type"] == "choice"
    assert result_dash["field"]["choices"] == ["individual", "family"]


def test_spain_student_visa_valid_individual_returns_eligible():
    result = evaluate_eligibility(
        _spain_student_payload(),
        pathway="spain-student-visa",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["pathway"] == "spain_student_visa"
    assert result["visa_type"] == "Spain Student Visa"


def test_spain_student_visa_insufficient_funds_returns_not_eligible():
    result = evaluate_eligibility(
        _spain_student_payload(monthly_funds_eur="599"),
        pathway="spain_student_visa",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["insufficient_financial_means"]


def test_spain_student_visa_family_route_calculates_dependent_funds():
    result = evaluate_eligibility(
        _spain_student_payload(
            applicant_type="family",
            dependents_count="2",
            monthly_funds_eur="1349",
        ),
        pathway="spain-student-visa",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["insufficient_financial_means"]
    assert result["required_monthly_financial_means_eur"] == 1350


def test_spain_student_visa_stay_over_6_months_triggers_background_logic():
    result = evaluate_eligibility(
        _spain_student_payload(background_check_available="no"),
        pathway="spain-student-visa",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["background_check_needs_review"]


def test_spain_student_visa_work_intent_can_return_needs_review():
    result = evaluate_eligibility(
        _spain_student_payload(
            study_category="training",
            student_work_intent="work_30_hours_or_less_and_study_compatible",
        ),
        pathway="spain-student-visa",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["student_work_authorization_needs_review"]


def test_spain_student_visa_individual_question_sequence():
    answers = {
        "routing.applicant_type": "individual",
        "identity.nationality": "United States",
        "identity.eu_eea_swiss_or_free_movement_status": "no",
        "routing.irregular_presence_spain": "no",
        "routing.application_route": "consular_outside_spain",
        "study.category": "higher_studies",
        "study.accepted_by_authorized_institution": "yes",
        "study.full_time_recognized_program": "yes",
        "study.modality": "hybrid",
        "study.in_person_requirement_met": "yes",
        "study.program_duration_months": "12",
        "study.stay_over_6_months": "yes",
        "study.application_timing_status": "at_least_2_months_before_start",
        "study.enrollment_payment_status": "paid_or_proven",
        "financial.monthly_funds_eur": "600",
        "financial.accommodation_prepaid_full_stay": "no",
        "financial.funds_evidence_types": ["bank_statements"],
        "routing.passport_validity_months": "24",
        "routing.health_insurance_status": "have_it",
        "identity.criminal_age_status": "yes",
        "routing.background_check_available": "yes",
        "routing.criminal_record_flag": "no",
        "routing.public_order_security_risk_flag": "no",
        "routing.public_health_disease_flag": "no",
        "study.student_work_intent": "no_work",
    }
    expected_order = list(answers.keys())

    payload: dict = {}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="spain-student-visa")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="spain-student-visa")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order


def test_spain_student_visa_no_escape_choices_anywhere_in_schema():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_student_visa"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    for field in data["taxonomy_fields"]:
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_spain_nlv_aliases_load_first_question():
    result_dash = evaluate({}, pathway="spain-nlv")
    result_underscore = evaluate({}, pathway="spain_nlv")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "routing.applicant_type"
    assert result_dash["field"]["input_type"] == "choice"
    assert result_dash["field"]["choices"] == ["individual", "family"]


def test_spain_nlv_valid_individual_returns_eligible():
    result = evaluate_eligibility(_spain_nlv_payload(), pathway="spain-nlv")

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["pathway"] == "spain_nlv"
    assert result["visa_type"] == "Spain Non-Lucrative Visa"


def test_spain_nlv_insufficient_funds_returns_not_eligible():
    result = evaluate_eligibility(
        _spain_nlv_payload(monthly_financial_means="2399"),
        pathway="spain_nlv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["insufficient_financial_means"]


def test_spain_nlv_family_route_calculates_dependent_threshold():
    result = evaluate_eligibility(
        _spain_nlv_payload(
            applicant_type="family",
            dependents_count="2",
            monthly_financial_means="3000",
        ),
        pathway="spain-nlv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["insufficient_financial_means"]
    assert result["required_monthly_financial_means_eur"] == 3600


def test_spain_nlv_individual_question_sequence():
    answers = {
        "routing.applicant_type": "individual",
        "identity.nationality": "United States",
        "identity.eu_eea_swiss_citizen": "no",
        "identity.eu_family_member_route": "no",
        "work.intends_to_work_in_spain": "no",
        "routing.irregular_presence_spain": "no",
        "financial.monthly_passive_income_or_assets_eur": "2400",
        "financial.funds_evidence_types": ["bank_certificates"],
        "financial.spanish_company_ownership": "no",
        "routing.passport_validity_months": "24",
        "routing.health_insurance_status": "have_it",
        "routing.background_check_available": "yes",
        "routing.criminal_record_flag": "no",
        "routing.public_order_security_risk_flag": "no",
        "routing.public_health_disease_flag": "no",
    }
    expected_order = [
        "routing.applicant_type",
        "identity.nationality",
        "identity.eu_eea_swiss_citizen",
        "identity.eu_family_member_route",
        "work.intends_to_work_in_spain",
        "routing.irregular_presence_spain",
        "financial.monthly_passive_income_or_assets_eur",
        "financial.funds_evidence_types",
        "financial.spanish_company_ownership",
        "routing.passport_validity_months",
        "routing.health_insurance_status",
        "routing.background_check_available",
        "routing.criminal_record_flag",
        "routing.public_order_security_risk_flag",
        "routing.public_health_disease_flag",
    ]

    payload = {"routing": {}}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="spain-nlv")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="spain-nlv")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order
    # The renewal question must never appear in the live flow.
    assert "routing.renewal_residence_days_expected" not in asked_keys


def test_spain_nlv_family_question_sequence():
    answers = {
        "routing.applicant_type": "family",
        "identity.nationality": "United States",
        "identity.eu_eea_swiss_citizen": "no",
        "identity.eu_family_member_route": "no",
        "work.intends_to_work_in_spain": "no",
        "routing.irregular_presence_spain": "no",
        "financial.monthly_passive_income_or_assets_eur": "3000",
        "financial.funds_evidence_types": ["bank_certificates"],
        "financial.spanish_company_ownership": "no",
        "routing.dependents_count": "1",
        "routing.dependent_relationships": "spouse",
        "routing.dependent_ages": "9",
        "routing.minor_children_schooling_status": "can_enroll",
        "routing.passport_validity_months": "24",
        "routing.health_insurance_status": "have_it",
        "routing.background_check_available": "yes",
        "routing.criminal_record_flag": "no",
        "routing.public_order_security_risk_flag": "no",
        "routing.public_health_disease_flag": "no",
    }
    expected_order = [
        "routing.applicant_type",
        "identity.nationality",
        "identity.eu_eea_swiss_citizen",
        "identity.eu_family_member_route",
        "work.intends_to_work_in_spain",
        "routing.irregular_presence_spain",
        "financial.monthly_passive_income_or_assets_eur",
        "financial.funds_evidence_types",
        "financial.spanish_company_ownership",
        "routing.dependents_count",
        "routing.dependent_relationships",
        "routing.dependent_ages",
        "routing.minor_children_schooling_status",
        "routing.passport_validity_months",
        "routing.health_insurance_status",
        "routing.background_check_available",
        "routing.criminal_record_flag",
        "routing.public_order_security_risk_flag",
        "routing.public_health_disease_flag",
    ]

    payload = {"routing": {}}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="spain-nlv")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="spain-nlv")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order
    assert "routing.renewal_residence_days_expected" not in asked_keys


def test_spain_nlv_eu_eea_swiss_citizen_hard_excludes_pathway():
    result = evaluate_eligibility(
        _spain_nlv_payload(eu_eea_swiss_citizen="yes"),
        pathway="spain-nlv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["eu_eea_swiss_citizen"]


def test_spain_nlv_eu_family_member_route_only_asked_when_not_citizen():
    payload = {
        "routing": {"applicant_type": "individual"},
        "identity": {"nationality": "United States", "eu_eea_swiss_citizen": "yes"},
    }

    result = evaluate(payload, pathway="spain-nlv")

    # Once eu_eea_swiss_citizen is "yes", the family-member question does not
    # apply (applies_when) and the flow moves straight past it.
    assert result["next_field_key"] != "identity.eu_family_member_route"


def test_spain_nlv_eu_family_member_route_hard_excludes_pathway():
    result = evaluate_eligibility(
        _spain_nlv_payload(eu_eea_swiss_citizen="no", eu_family_member_route="yes"),
        pathway="spain-nlv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["eu_family_member_route"]


def test_spain_nlv_neither_eu_citizen_nor_family_member_continues():
    result = evaluate_eligibility(
        _spain_nlv_payload(eu_eea_swiss_citizen="no", eu_family_member_route="no"),
        pathway="spain-nlv",
    )

    assert "eu_eea_swiss_citizen" not in result["failed_requirements"]
    assert "eu_family_member_route" not in result["failed_requirements"]


def test_spain_nlv_work_intent_polarity():
    # Planning to work in Spain is a hard failure.
    working = evaluate_eligibility(
        _spain_nlv_payload(intends_to_work_in_spain="yes"),
        pathway="spain-nlv",
    )
    assert working["eligibility_status"] == "not_eligible"
    assert working["failed_requirements"] == ["work_activity_in_spain"]

    # Not planning to work passes this requirement.
    not_working = evaluate_eligibility(
        _spain_nlv_payload(intends_to_work_in_spain="no"),
        pathway="spain-nlv",
    )
    assert "work_activity_in_spain" not in not_working["failed_requirements"]
    assert "work_intent_needs_review" not in not_working["failed_requirements"]


def test_spain_nlv_spanish_company_labor_activity_polarity():
    # Performing labor for the Spanish company funding the case is a hard failure.
    performs_labor = evaluate_eligibility(
        _spain_nlv_payload(
            spanish_company_ownership="yes",
            performs_labor_for_spanish_company="yes",
        ),
        pathway="spain-nlv",
    )
    assert performs_labor["eligibility_status"] == "not_eligible"
    assert performs_labor["failed_requirements"] == ["spanish_company_labor_activity"]

    # Not performing labor for it passes.
    no_labor = evaluate_eligibility(
        _spain_nlv_payload(
            spanish_company_ownership="yes",
            performs_labor_for_spanish_company="no",
        ),
        pathway="spain-nlv",
    )
    assert "spanish_company_labor_activity" not in no_labor["failed_requirements"]

    # Unclear/missing answer is a soft needs_review, not a hard failure.
    unclear = evaluate_eligibility(
        _spain_nlv_payload(
            monthly_financial_means="2400",
            spanish_company_ownership="yes",
        ),
        pathway="spain-nlv",
    )
    assert unclear["eligibility_status"] == "needs_review"
    assert unclear["failed_requirements"] == [
        "spanish_company_labor_activity_needs_review"
    ]


def test_spain_nlv_minor_children_schooling_branch():
    cannot_enroll = evaluate_eligibility(
        _spain_nlv_payload(
            applicant_type="family",
            monthly_financial_means="3000",
            minor_children_schooling_status="cannot_enroll",
        ),
        pathway="spain-nlv",
    )
    assert cannot_enroll["eligibility_status"] == "needs_review"
    assert "minor_children_schooling_issue" in cannot_enroll["failed_requirements"]
    # Schooling issues are conditional/review, never a hard failure.
    import app.engine.pathways.spain_nlv.rules as spain_nlv_rules

    assert "minor_children_schooling_issue" not in spain_nlv_rules.HARD_FAILURES

    can_enroll = evaluate_eligibility(
        _spain_nlv_payload(
            applicant_type="family",
            monthly_financial_means="3000",
            minor_children_schooling_status="can_enroll",
        ),
        pathway="spain-nlv",
    )
    assert "minor_children_schooling_issue" not in can_enroll["failed_requirements"]

    no_minor_children = evaluate_eligibility(
        _spain_nlv_payload(
            applicant_type="family",
            monthly_financial_means="3000",
            minor_children_schooling_status="no_minor_children",
        ),
        pathway="spain-nlv",
    )
    assert no_minor_children["eligibility_status"] == "eligible"


def test_spain_nlv_health_insurance_three_state_behavior():
    have_it = evaluate_eligibility(
        _spain_nlv_payload(health_insurance_status="have_it"), pathway="spain-nlv"
    )
    assert have_it["eligibility_status"] == "eligible"

    will_obtain = evaluate_eligibility(
        _spain_nlv_payload(health_insurance_status="will_obtain"), pathway="spain-nlv"
    )
    assert will_obtain["eligibility_status"] == "needs_review"
    assert will_obtain["failed_requirements"] == ["health_insurance_needs_review"]

    cannot_obtain = evaluate_eligibility(
        _spain_nlv_payload(health_insurance_status="cannot_obtain"), pathway="spain-nlv"
    )
    assert cannot_obtain["eligibility_status"] == "not_eligible"
    assert cannot_obtain["failed_requirements"] == ["health_insurance_unavailable"]


def test_spain_nlv_background_check_availability_choices_are_binary():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_nlv"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    field = next(
        f
        for f in data["taxonomy_fields"]
        if f["key"] == "routing.background_check_available"
    )
    assert field["choices"] == ["yes", "no"]


def test_spain_nlv_criminal_record_disclosure_is_manual_review_not_hard_failure():
    disclosed = evaluate_eligibility(
        _spain_nlv_payload(criminal_record_flag="yes"), pathway="spain-nlv"
    )
    assert disclosed["eligibility_status"] == "needs_review"
    assert disclosed["failed_requirements"] == ["criminal_record_needs_review"]

    import app.engine.pathways.spain_nlv.rules as spain_nlv_rules

    assert "criminal_record_needs_review" not in spain_nlv_rules.HARD_FAILURES
    assert "criminal_record_flag" not in spain_nlv_rules.HARD_FAILURES


def test_spain_nlv_public_order_security_risk_is_hard_failure():
    result = evaluate_eligibility(
        _spain_nlv_payload(public_order_security_risk_flag="yes"),
        pathway="spain-nlv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["public_order_security_risk"]


def test_spain_nlv_public_health_disease_is_hard_failure():
    result = evaluate_eligibility(
        _spain_nlv_payload(public_health_disease_flag="yes"),
        pathway="spain-nlv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["serious_public_health_disease"]


def test_spain_nlv_renewal_question_absent_from_live_taxonomy_fields():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_nlv"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    live_keys = {f["key"] for f in data["taxonomy_fields"]}
    assert "routing.renewal_residence_days_expected" not in live_keys

    checklist_keys = {
        f["key"] for f in data.get("post_eligibility_checklist", {}).get("fields", [])
    }
    assert "routing.renewal_residence_days_expected" in checklist_keys

    import app.engine.pathways.spain_nlv.rules as spain_nlv_rules
    import inspect

    source = inspect.getsource(spain_nlv_rules.evaluate_eligibility)
    assert "renewal_residence_days_expected" not in source


def test_spain_nlv_no_escape_choices_anywhere_in_schema():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_nlv"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    for field in data["taxonomy_fields"]:
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_italy_elective_residence_aliases_load_first_question():
    result_dash = evaluate({}, pathway="italy-elective-residence")
    result_underscore = evaluate({}, pathway="italy_elective_residence")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "routing.applicant_type"
    assert result_dash["field"]["input_type"] == "choice"
    assert result_dash["field"]["choices"] == ["individual", "family"]


def test_italy_elective_residence_valid_individual_returns_eligible():
    result = evaluate_eligibility(
        _italy_elective_residence_payload(),
        pathway="italy-elective-residence",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["pathway"] == "italy_elective_residence"
    assert result["visa_type"] == "Italy Elective Residence Visa"


def test_italy_elective_residence_work_intent_returns_not_eligible():
    result = evaluate_eligibility(
        _italy_elective_residence_payload(intends_to_work_in_italy="yes"),
        pathway="italy-elective-residence",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["no_work_in_italy_not_confirmed"]

    passes = evaluate_eligibility(
        _italy_elective_residence_payload(intends_to_work_in_italy="no"),
        pathway="italy-elective-residence",
    )
    assert "no_work_in_italy_not_confirmed" not in passes["failed_requirements"]


def test_italy_elective_residence_insufficient_income_assets_not_eligible():
    result = evaluate_eligibility(
        _italy_elective_residence_payload(
            annual_passive_income_eur="30000",
            available_assets_eur="0",
        ),
        pathway="italy_elective_residence",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert "insufficient_passive_income" in result["failed_requirements"]
    assert "financial_assets_need_review" in result["failed_requirements"]


def test_italy_elective_residence_missing_lodging_returns_not_eligible():
    result = evaluate_eligibility(
        _italy_elective_residence_payload(italy_lodging_status="not_available"),
        pathway="italy-elective-residence",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["qualifying_italian_lodging_unavailable"]


def test_italy_elective_residence_family_route_can_return_needs_review():
    result = evaluate_eligibility(
        _italy_elective_residence_payload(
            applicant_type="family",
            annual_passive_income_eur="70000",
            family_documents_available="no",
        ),
        pathway="italy-elective-residence",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == ["family_documents_needs_review"]
    assert result["required_annual_passive_income_eur"] == 62000


def test_italy_elective_residence_individual_question_sequence():
    answers = {
        "routing.applicant_type": "individual",
        "identity.nationality": "United States",
        "routing.consulate_jurisdiction": "new_york",
        "work.intends_to_work_in_italy": "no",
        "routing.stable_residence_intent": "stable_residence",
        "financial.annual_passive_income_eur": "50000",
        "financial.available_assets_eur": "250000",
        "financial.income_source_types": ["pension"],
        "financial.income_evidence_types": ["bank_letters"],
        "financial.tax_returns_available": "two_years_complete_with_schedules",
        "housing.italy_lodging_status": "registered_lease",
        "routing.health_insurance_status": "have_it",
        "routing.health_insurance_coverage_level": "meets_consular_coverage",
        "routing.passport_validity_months": "24",
        "routing.passport_issued_within_10_years": "yes",
        "routing.passport_blank_pages": "2",
        "compliance.permesso_8_day_acknowledged": "yes",
        "compliance.annual_renewal_acknowledged": "yes",
    }
    expected_order = list(answers.keys())

    payload = {"routing": {}}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="italy-elective-residence")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="italy-elective-residence")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order
    assert "consulate.additional_documents_acknowledged" not in asked_keys


def test_italy_elective_residence_consulate_discretion_removed():
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "italy_elective_residence"
        / "questions.json"
    )
    import json

    data = json.loads(questions_path.read_text(encoding="utf-8"))
    live_keys = {f["key"] for f in data["taxonomy_fields"]}
    assert "consulate.additional_documents_acknowledged" not in live_keys

    import app.engine.pathways.italy_elective_residence.rules as italy_er_rules
    import inspect

    source = inspect.getsource(italy_er_rules.evaluate_eligibility)
    assert '"consulate.additional_documents_acknowledged"' not in source

    # A fully answered payload omitting the removed field entirely must still
    # be able to reach "eligible".
    result = evaluate_eligibility(
        _italy_elective_residence_payload(), pathway="italy-elective-residence"
    )
    assert result["eligibility_status"] == "eligible"


def test_italy_elective_residence_permesso_and_renewal_untouched_pending_legal_review():
    """Section 3 items: these two questions still carry HARD_FAILURES codes and
    still offer 'not_sure' -- explicitly left unchanged pending a legal-review
    decision, not touched by this Batch 1 cleanup."""
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "italy_elective_residence"
        / "questions.json"
    )
    import json

    data = json.loads(questions_path.read_text(encoding="utf-8"))
    fields_by_key = {f["key"]: f for f in data["taxonomy_fields"]}

    assert fields_by_key["compliance.permesso_8_day_acknowledged"]["choices"] == [
        "yes",
        "no",
        "not_sure",
    ]
    assert fields_by_key["compliance.annual_renewal_acknowledged"]["choices"] == [
        "yes",
        "no",
        "not_sure",
    ]

    import app.engine.pathways.italy_elective_residence.rules as italy_er_rules

    assert "permesso_acknowledgement_missing" in italy_er_rules.HARD_FAILURES
    assert "renewal_acknowledgement_missing" in italy_er_rules.HARD_FAILURES


def test_italy_elective_residence_no_escape_choices_outside_section_3_items():
    """Zero escape choices anywhere EXCEPT the two Section-3 items explicitly
    left untouched pending legal review."""
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "italy_elective_residence"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    allowed_exceptions = {
        "compliance.permesso_8_day_acknowledged",
        "compliance.annual_renewal_acknowledged",
    }
    for field in data["taxonomy_fields"]:
        if field["key"] in allowed_exceptions:
            continue
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_portugal_d7_aliases_load_first_question():
    result_dash = evaluate({}, pathway="portugal-d7")
    result_underscore = evaluate({}, pathway="portugal_d7")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "routing.applicant_type"
    assert result_dash["field"]["input_type"] == "choice"
    assert result_dash["field"]["choices"] == ["individual", "family"]


def test_portugal_d7_valid_individual_returns_eligible():
    result = evaluate_eligibility(_portugal_d7_payload(), pathway="portugal-d7")

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["pathway"] == "portugal_d7"
    assert result["visa_type"] == "Portugal D7 Passive Income Visa"


def test_portugal_d7_insufficient_income_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_d7_payload(annual_passive_income_eur="11039"),
        pathway="portugal_d7",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["insufficient_passive_income"]


def test_portugal_d7_active_employment_intent_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_d7_payload(passive_own_income_intent="no"),
        pathway="portugal-d7",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["active_employment_or_non_passive_intent"]


def test_portugal_d7_missing_portugal_income_availability_not_eligible():
    result = evaluate_eligibility(
        _portugal_d7_payload(portuguese_bank_availability="no"),
        pathway="portugal-d7",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["income_not_available_in_portugal"]


def test_portugal_d7_missing_12_month_accommodation_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_d7_payload(portugal_accommodation_12_months="not_available"),
        pathway="portugal-d7",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == [
        "portugal_accommodation_12_months_unavailable"
    ]


def test_portugal_d7_family_route_applies_dependent_income_formula():
    result = evaluate_eligibility(
        _portugal_d7_payload(
            applicant_type="family",
            annual_passive_income_eur="19871",
        ),
        pathway="portugal-d7",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["insufficient_passive_income"]
    assert result["required_annual_passive_income_eur"] == 19872
    assert result["dependent_income_formula"] == {
        "main_applicant": "100%",
        "additional_adult": "50%",
        "child_or_dependent_non_minor": "30%",
    }


def test_portugal_d7_background_gaps_can_return_needs_review():
    result = evaluate_eligibility(
        _portugal_d7_payload(
            police_clearance_available="not_sure",
            criminal_record_flag="yes",
        ),
        pathway="portugal-d7",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "police_clearance_needs_review",
        "criminal_record_needs_review",
    ]


def test_portugal_d7_individual_question_sequence():
    answers = {
        "routing.applicant_type": "individual",
        "identity.nationality": "United States",
        "routing.application_country_matches_nationality": "yes",
        "routing.passive_own_income_intent": "yes",
        "financial.annual_passive_income_eur": "20000",
        "financial.income_source_types": ["pension"],
        "financial.income_evidence_types": ["bank_statements"],
        "financial.portuguese_bank_availability": "yes",
        "housing.portugal_accommodation_12_months": "lease_12_months_or_more",
        "routing.passport_validity_months": "12",
        "routing.health_travel_insurance_status": "have_it",
        "routing.police_clearance_available": "yes",
        "routing.criminal_record_flag": "no",
        "compliance.truthful_documents_acknowledged": "yes",
    }
    expected_order = list(answers.keys())

    payload = {"routing": {}}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="portugal-d7")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="portugal-d7")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order
    assert "compliance.aima_residence_step_acknowledged" not in asked_keys
    assert "consulate.discretion_extra_documents_acknowledged" not in asked_keys


def test_portugal_d7_relocated_and_removed_questions():
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_d7"
        / "questions.json"
    )
    import json

    data = json.loads(questions_path.read_text(encoding="utf-8"))

    live_keys = {f["key"] for f in data["taxonomy_fields"]}
    assert "compliance.aima_residence_step_acknowledged" not in live_keys
    assert "consulate.discretion_extra_documents_acknowledged" not in live_keys

    checklist_keys = {
        f["key"] for f in data.get("post_eligibility_checklist", {}).get("fields", [])
    }
    assert "compliance.aima_residence_step_acknowledged" in checklist_keys
    assert "consulate.discretion_extra_documents_acknowledged" not in checklist_keys

    import app.engine.pathways.portugal_d7.rules as portugal_d7_rules

    source_text = Path(
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_d7"
        / "rules.py"
    ).read_text(encoding="utf-8")
    assert '"compliance.aima_residence_step_acknowledged"' not in source_text
    assert '"consulate.discretion_extra_documents_acknowledged"' not in source_text

    result = evaluate_eligibility(_portugal_d7_payload(), pathway="portugal-d7")
    assert result["eligibility_status"] == "eligible"


def test_portugal_d7_truthful_documents_untouched_pending_legal_review():
    """Section 3 item: this question still carries a HARD_FAILURES code and
    still offers 'not_sure' -- explicitly left unchanged pending a legal-review
    decision, not touched by this Batch 1 cleanup."""
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_d7"
        / "questions.json"
    )
    import json

    data = json.loads(questions_path.read_text(encoding="utf-8"))
    fields_by_key = {f["key"]: f for f in data["taxonomy_fields"]}

    assert fields_by_key["compliance.truthful_documents_acknowledged"]["choices"] == [
        "yes",
        "no",
        "not_sure",
    ]

    import app.engine.pathways.portugal_d7.rules as portugal_d7_rules

    assert "false_statement_risk_not_acknowledged" in portugal_d7_rules.HARD_FAILURES


def test_portugal_d7_no_escape_choices_outside_section_3_items():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_d7"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    allowed_exceptions = {"compliance.truthful_documents_acknowledged"}
    for field in data["taxonomy_fields"]:
        if field["key"] in allowed_exceptions:
            continue
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_portugal_dnv_aliases_load_first_question():
    result_dash = evaluate({}, pathway="portugal-dnv")
    result_underscore = evaluate({}, pathway="portugal_dnv")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "routing.visa_route"
    assert result_dash["field"]["input_type"] == "choice"
    assert result_dash["field"]["choices"] == [
        "residence_visa",
        "temporary_stay_under_1_year",
    ]


def test_portugal_dnv_valid_remote_employee_returns_eligible():
    result = evaluate_eligibility(_portugal_dnv_payload(), pathway="portugal-dnv")

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["pathway"] == "portugal_dnv"
    assert result["work_type"] == "remote_employee"
    assert result["minimum_average_monthly_income_eur"] == 3680


def test_portugal_dnv_valid_independent_freelancer_returns_eligible():
    result = evaluate_eligibility(
        _portugal_dnv_payload(work_relationship="freelancer_independent"),
        pathway="portugal-digital-nomad",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["work_type"] == "freelancer_independent"


def test_portugal_dnv_valid_business_owner_company_service_returns_eligible():
    result = evaluate_eligibility(
        _portugal_dnv_payload(work_relationship="business_owner_company_service"),
        pathway="portugal-remote-work-visa",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["work_type"] == "business_owner_company_service"


def test_portugal_dnv_income_below_threshold_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_dnv_payload(average_monthly_income_last_3_months_eur="3679"),
        pathway="portugal-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["income_below_minimum"]


def test_portugal_dnv_non_foreign_remote_work_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_dnv_payload(entities_outside_portugal="no"),
        pathway="portugal-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == [
        "remote_work_not_for_entities_outside_portugal"
    ]


def test_portugal_dnv_missing_role_specific_work_proof_returns_expected_status():
    missing_employee = evaluate_eligibility(
        _portugal_dnv_payload(employee_contract_or_declaration_available="no"),
        pathway="portugal-dnv",
    )
    unclear_independent = evaluate_eligibility(
        _portugal_dnv_payload(
            work_relationship="freelancer_independent",
            independent_service_or_client_proof_available="not_sure",
        ),
        pathway="portugal-dnv",
    )

    assert missing_employee["eligibility_status"] == "not_eligible"
    assert missing_employee["failed_requirements"] == [
        "employee_contract_or_declaration_unavailable"
    ]
    assert unclear_independent["eligibility_status"] == "needs_review"
    assert unclear_independent["failed_requirements"] == [
        "independent_service_or_client_proof_needs_review"
    ]


def test_portugal_dnv_missing_tax_residence_certificate_returns_expected_status():
    missing = evaluate_eligibility(
        _portugal_dnv_payload(tax_residence_certificate_available="no"),
        pathway="portugal-dnv",
    )
    unclear = evaluate_eligibility(
        _portugal_dnv_payload(tax_residence_certificate_available="not_sure"),
        pathway="portugal-dnv",
    )

    assert missing["eligibility_status"] == "not_eligible"
    assert missing["failed_requirements"] == ["tax_residence_certificate_unavailable"]
    assert unclear["eligibility_status"] == "needs_review"
    assert unclear["failed_requirements"] == ["tax_residence_certificate_needs_review"]


def test_portugal_dnv_temporary_stay_route_returns_eligible():
    result = evaluate_eligibility(
        _portugal_dnv_payload(visa_route="temporary_stay_under_1_year"),
        pathway="portugal-dnv",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []


def test_portugal_dnv_individual_question_sequence():
    answers = {
        "routing.visa_route": "residence_visa",
        "routing.work_relationship": "remote_employee",
        "work.entities_outside_portugal": "yes",
        "role.employee.contract_or_declaration_available": "yes",
        "financial.average_monthly_income_last_3_months_eur": "3680",
        "financial.income_evidence_types": ["bank_statements"],
        "documents.tax_residence_certificate_available": "yes",
        "routing.applicant_type": "individual",
        "identity.nationality": "United States",
        "routing.application_country_matches_nationality": "yes",
        "routing.passport_validity_months": "12",
        "routing.health_travel_insurance_status": "have_it",
        "routing.police_clearance_available": "yes",
        "routing.criminal_record_flag": "no",
        "routing.removal_or_refusal_alert_flag": "no",
        "housing.settlement_statement_ready": "yes",
        "compliance.truthful_documents_acknowledged": "yes",
    }
    expected_order = list(answers.keys())

    payload = {"routing": {}}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="portugal-dnv")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="portugal-dnv")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order
    assert "compliance.aima_residence_permit_acknowledged" not in asked_keys
    assert "compliance.renewal_acknowledged" not in asked_keys
    assert "consulate.discretion_extra_documents_acknowledged" not in asked_keys


def test_portugal_dnv_relocated_questions_do_not_affect_eligibility():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_dnv"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    live_keys = {f["key"] for f in data["taxonomy_fields"]}
    assert "compliance.aima_residence_permit_acknowledged" not in live_keys
    assert "compliance.renewal_acknowledged" not in live_keys
    assert "consulate.discretion_extra_documents_acknowledged" not in live_keys

    checklist_keys = {
        f["key"] for f in data.get("post_eligibility_checklist", {}).get("fields", [])
    }
    assert "compliance.aima_residence_permit_acknowledged" in checklist_keys
    assert "compliance.renewal_acknowledged" in checklist_keys
    assert "consulate.discretion_extra_documents_acknowledged" not in checklist_keys

    import app.engine.pathways.portugal_dnv.rules as portugal_dnv_rules

    source_text = Path(
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_dnv"
        / "rules.py"
    ).read_text(encoding="utf-8")
    assert '"compliance.aima_residence_permit_acknowledged"' not in source_text
    assert '"compliance.renewal_acknowledged"' not in source_text
    assert '"consulate.discretion_extra_documents_acknowledged"' not in source_text

    # A payload without these fields at all is still fully evaluable and eligible.
    result = evaluate_eligibility(_portugal_dnv_payload(), pathway="portugal-dnv")
    assert result["eligibility_status"] == "eligible"


def test_portugal_dnv_truthful_documents_untouched_pending_legal_review():
    """Section 3 item: still carries a HARD_FAILURES code and still offers
    'not_sure' -- explicitly left unchanged pending legal review."""
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_dnv"
        / "questions.json"
    )
    import json

    data = json.loads(questions_path.read_text(encoding="utf-8"))
    fields_by_key = {f["key"]: f for f in data["taxonomy_fields"]}

    assert fields_by_key["compliance.truthful_documents_acknowledged"]["choices"] == [
        "yes",
        "no",
        "not_sure",
    ]

    import app.engine.pathways.portugal_dnv.rules as portugal_dnv_rules

    assert "truthful_documents_not_acknowledged" in portugal_dnv_rules.HARD_FAILURES


def test_portugal_dnv_no_escape_choices_outside_section_3_items():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_dnv"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    allowed_exceptions = {"compliance.truthful_documents_acknowledged"}
    for field in data["taxonomy_fields"]:
        if field["key"] in allowed_exceptions:
            continue
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_portugal_dnv_family_route_can_return_needs_review():
    result = evaluate_eligibility(
        _portugal_dnv_payload(
            applicant_type="family",
            family_documents_available="no",
            family_stable_means_available="not_sure",
        ),
        pathway="portugal-dnv",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "family_documents_needs_review",
        "family_stable_means_needs_review",
    ]


def test_portugal_golden_visa_aliases_load_first_question():
    result_dash = evaluate({}, pathway="portugal-golden-visa")
    result_underscore = evaluate({}, pathway="portugal_golden_visa")

    assert result_dash == result_underscore
    assert result_dash["next_field_key"] == "identity.nationality"
    assert result_dash["field"]["input_type"] == "text"


def test_portugal_golden_visa_non_third_country_national_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(
            third_country_national_status="portuguese_eu_eea_andorra_swiss"
        ),
        pathway="portugal-golden-visa",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == [
        "portuguese_eu_eea_andorra_swiss_national"
    ]


def test_portugal_golden_visa_real_estate_only_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(investment_route="real_estate_only"),
        pathway="portugal-ari",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["real_estate_only_basis"]


def test_portugal_golden_visa_valid_job_creation_returns_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(investment_route="job_creation"),
        pathway="portugal-golden-visa",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["investment_route"] == "job_creation"
    assert result["pathway"] == "portugal_golden_visa"


def test_portugal_golden_visa_valid_scientific_research_returns_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(investment_route="scientific_research"),
        pathway="portugal_ari",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["investment_route"] == "scientific_research"


def test_portugal_golden_visa_valid_arts_cultural_heritage_returns_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(investment_route="arts_cultural_heritage"),
        pathway="portugal-investment-residence",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["investment_route"] == "arts_cultural_heritage"


def test_portugal_golden_visa_valid_non_real_estate_fund_returns_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(
            investment_route="non_real_estate_investment_fund"
        ),
        pathway="portugal-investment-residence-permit",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["investment_route"] == "non_real_estate_investment_fund"


def test_portugal_golden_visa_valid_company_capitalization_returns_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(investment_route="company_capitalization_jobs"),
        pathway="portugal-golden-visa",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []
    assert result["investment_route"] == "company_capitalization_jobs"


def test_portugal_golden_visa_below_route_threshold_returns_not_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(
            investment_route="scientific_research",
            scientific_research_amount_eur="499999",
        ),
        pathway="portugal-golden-visa",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == [
        "scientific_research_amount_below_minimum"
    ]


def test_portugal_golden_visa_missing_route_evidence_returns_expected_status():
    missing = evaluate_eligibility(
        _portugal_golden_visa_payload(job_creation_evidence_available="no"),
        pathway="portugal-golden-visa",
    )
    unclear = evaluate_eligibility(
        _portugal_golden_visa_payload(
            investment_route="non_real_estate_investment_fund",
            fund_non_real_estate_confirmed="not_sure",
        ),
        pathway="portugal-golden-visa",
    )

    assert missing["eligibility_status"] == "not_eligible"
    assert missing["failed_requirements"] == ["job_creation_evidence_unavailable"]
    assert unclear["eligibility_status"] == "needs_review"
    assert unclear["failed_requirements"] == ["fund_non_real_estate_status_needs_review"]


def test_portugal_golden_visa_serious_criminal_conviction_not_eligible():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(serious_criminal_conviction_flag="yes"),
        pathway="portugal-golden-visa",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["serious_criminal_conviction"]


def test_portugal_golden_visa_entry_ban_or_refusal_alert_not_eligible():
    entry_ban = evaluate_eligibility(
        _portugal_golden_visa_payload(entry_stay_ban_flag="yes"),
        pathway="portugal-golden-visa",
    )
    refusal_alert = evaluate_eligibility(
        _portugal_golden_visa_payload(sii_ucfe_refusal_alert_flag="yes"),
        pathway="portugal-golden-visa",
    )

    assert entry_ban["eligibility_status"] == "not_eligible"
    assert entry_ban["failed_requirements"] == ["entry_stay_ban"]
    assert refusal_alert["eligibility_status"] == "not_eligible"
    assert refusal_alert["failed_requirements"] == ["sii_ucfe_refusal_alert"]


def test_portugal_golden_visa_tax_or_social_security_gaps_expected_status():
    tax_debt = evaluate_eligibility(
        _portugal_golden_visa_payload(
            portuguese_tax_clearance_status="has_tax_debts"
        ),
        pathway="portugal-golden-visa",
    )
    social_unclear = evaluate_eligibility(
        _portugal_golden_visa_payload(social_security_clearance_status="not_sure"),
        pathway="portugal-golden-visa",
    )

    assert tax_debt["eligibility_status"] == "not_eligible"
    assert tax_debt["failed_requirements"] == ["portuguese_tax_debts"]
    assert social_unclear["eligibility_status"] == "needs_review"
    assert social_unclear["failed_requirements"] == [
        "social_security_clearance_needs_review"
    ]


def test_portugal_golden_visa_family_route_can_return_needs_review():
    result = evaluate_eligibility(
        _portugal_golden_visa_payload(
            applicant_type="family",
            family_documents_available="no",
        ),
        pathway="portugal-golden-visa",
    )

    assert result["eligibility_status"] == "needs_review"
    assert result["failed_requirements"] == [
        "family_documents_needs_review",
    ]


def test_portugal_golden_visa_individual_question_sequence():
    answers = {
        "identity.nationality": "United States",
        "identity.third_country_national_status": "third_country_national",
        "investment.route": "job_creation",
        "investment.real_estate_only_basis": "no",
        "investment.job_creation.jobs_created_count": "10",
        "investment.job_creation.evidence_available": "yes",
        "investment.proof_of_funds_or_transfer_available": "yes",
        "routing.applicant_type": "individual",
        "documents.valid_passport_available": "yes",
        "documents.criminal_record_certificate_available": (
            "yes_recent_translated_apostilled"
        ),
        "routing.serious_criminal_conviction_flag": "no",
        "routing.entry_stay_ban_flag": "no",
        "routing.sii_ucfe_refusal_alert_flag": "no",
        "documents.portuguese_tax_clearance_status": "debt_clearance_certificate",
        "documents.social_security_clearance_status": "debt_clearance_certificate",
        "documents.foreign_tax_id_disclosure_available": "yes",
        "compliance.investment_maintenance_declaration_available": "yes",
    }
    expected_order = list(answers.keys())

    payload: dict = {}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="portugal-golden-visa")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="portugal-golden-visa")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order
    assert "process.portal_ari_family_application_acknowledged" not in asked_keys
    assert "compliance.minimum_stay_acknowledged" not in asked_keys
    assert "process.portal_ari_acknowledged" not in asked_keys
    assert "compliance.renewal_investment_maintenance_acknowledged" not in asked_keys
    assert "compliance.permanent_residence_later_stage_acknowledged" not in asked_keys


def test_portugal_golden_visa_relocated_and_removed_questions():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_golden_visa"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    live_keys = {f["key"] for f in data["taxonomy_fields"]}
    assert "process.portal_ari_family_application_acknowledged" not in live_keys
    assert "compliance.minimum_stay_acknowledged" not in live_keys
    assert "process.portal_ari_acknowledged" not in live_keys
    assert "compliance.renewal_investment_maintenance_acknowledged" not in live_keys
    assert "compliance.permanent_residence_later_stage_acknowledged" not in live_keys

    checklist_keys = {
        f["key"] for f in data.get("post_eligibility_checklist", {}).get("fields", [])
    }
    assert checklist_keys == {
        "compliance.minimum_stay_acknowledged",
        "compliance.renewal_investment_maintenance_acknowledged",
    }

    import app.engine.pathways.portugal_golden_visa.rules as portugal_golden_visa_rules

    source_text = Path(
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_golden_visa"
        / "rules.py"
    ).read_text(encoding="utf-8")
    for removed_key in (
        '"process.portal_ari_family_application_acknowledged"',
        '"compliance.minimum_stay_acknowledged"',
        '"process.portal_ari_acknowledged"',
        '"compliance.renewal_investment_maintenance_acknowledged"',
        '"compliance.permanent_residence_later_stage_acknowledged"',
    ):
        assert removed_key not in source_text

    result = evaluate_eligibility(
        _portugal_golden_visa_payload(), pathway="portugal-golden-visa"
    )
    assert result["eligibility_status"] == "eligible"


def test_portugal_golden_visa_investment_routes_untouched_pending_legal_review():
    """Section 3 items: the 5 investment-route evidence questions and the
    investment-maintenance declaration still carry HARD_FAILURES codes --
    only their escape choices were removed, not touched otherwise."""
    import app.engine.pathways.portugal_golden_visa.rules as portugal_golden_visa_rules

    for code in (
        "job_creation_evidence_unavailable",
        "scientific_research_institution_confirmation_unavailable",
        "arts_cultural_heritage_qualifying_entity_unavailable",
        "fund_subscription_documents_unavailable",
        "company_capitalization_documents_unavailable",
        "investment_maintenance_declaration_unavailable",
    ):
        assert code in portugal_golden_visa_rules.HARD_FAILURES


def test_portugal_golden_visa_no_escape_choices_anywhere_in_schema():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "portugal_golden_visa"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    for field in data["taxonomy_fields"]:
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


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
    assert result["next_field_key"] == "work.intends_to_work_in_costa_rica"


def test_costa_rica_pensionado_uses_dnv_style_income_order():
    payload = {
        "routing": {
            "applicant_type": "individual",
        },
        "work": {"intends_to_work_in_costa_rica": "no"},
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
        },
        "work": {"intends_to_work_in_costa_rica": "no"},
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


def test_costa_rica_pensionado_work_intent_polarity():
    working = evaluate_eligibility(
        _pensionado_payload(intends_to_work_in_costa_rica="yes"),
        pathway="costa-rica-pensionado",
    )
    assert working["failed_requirements"] == ["work_authorization_acknowledgement_missing"]
    assert working["eligibility_status"] == "needs_review"

    not_working = evaluate_eligibility(
        _pensionado_payload(intends_to_work_in_costa_rica="no"),
        pathway="costa-rica-pensionado",
    )
    assert "work_authorization_acknowledgement_missing" not in not_working["failed_requirements"]
    assert not_working["eligibility_status"] == "eligible"


def test_costa_rica_pensionado_individual_question_sequence():
    answers = {
        "routing.applicant_type": "individual",
        "role.pensionado.retired_from_habitual_occupation": "yes",
        "role.pensionado.pension_source_type": "social_security",
        "role.pensionado.pension_retirement_based": "yes",
        "work.intends_to_work_in_costa_rica": "no",
        "role.pensionado.pension_foreign_source_confirmed": "yes",
        "role.pensionado.monthly_pension_usd": "1000",
        "role.pensionado.pension_certificate_available": "yes",
        "role.pensionado.pension_duration_type": "lifetime_or_indefinite",
        "identity.nationality": "United States",
        "identity.country_of_residence": "United States",
        "routing.passport_validity_months": "24",
        "documents.passport_copy_available": "yes",
        "documents.police_clearance_available": "yes",
        "routing.criminal_record_flag": "no",
        "documents.birth_certificate_available": "yes",
        "documents.passport_photos_available": "yes",
        "documents.filiacion_form_ready": "yes",
        "documents.request_letter_ready": "yes",
        "documents.government_fees_ready": "yes",
        "documents.apostille_translation_ready": "yes",
        "documents.pension_receipt_costa_rica_evidence_available": "can_document",
    }
    expected_order = list(answers.keys())

    payload = {"routing": {}}
    asked_keys = []
    for expected_key in expected_order:
        result = evaluate(payload, pathway="costa-rica-pensionado")
        assert result["next_field_key"] == expected_key
        asked_keys.append(result["next_field_key"])
        current = payload
        parts = expected_key.split(".")
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = answers[expected_key]

    result = evaluate(payload, pathway="costa-rica-pensionado")
    assert result["next_field_key"] is None
    assert asked_keys == expected_order
    # Relocated/removed questions must never appear in the live flow.
    assert "documents.ccss_renewal_ready" not in asked_keys
    assert "routing.temporary_residence_acknowledged" not in asked_keys
    assert "routing.renewal_every_two_years_acknowledged" not in asked_keys


def test_costa_rica_pensionado_relocated_questions_do_not_affect_eligibility():
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "costa_rica_pensionado"
        / "questions.json"
    )
    import json

    data = json.loads(questions_path.read_text(encoding="utf-8"))

    live_keys = {f["key"] for f in data["taxonomy_fields"]}
    assert "documents.ccss_renewal_ready" not in live_keys
    assert "routing.temporary_residence_acknowledged" not in live_keys
    assert "routing.renewal_every_two_years_acknowledged" not in live_keys

    checklist_keys = {
        f["key"] for f in data.get("post_eligibility_checklist", {}).get("fields", [])
    }
    assert "documents.ccss_renewal_ready" in checklist_keys
    assert "routing.renewal_every_two_years_acknowledged" in checklist_keys
    # temporary_residence_acknowledged was removed outright (not preserved).
    assert "routing.temporary_residence_acknowledged" not in checklist_keys

    import app.engine.pathways.costa_rica_pensionado.rules as pensionado_rules
    import inspect

    source = inspect.getsource(pensionado_rules.evaluate_eligibility)
    assert '"documents.ccss_renewal_ready"' not in source
    assert '"routing.temporary_residence_acknowledged"' not in source
    assert '"routing.renewal_every_two_years_acknowledged"' not in source

    # A fully answered payload omitting the relocated/removed fields entirely
    # must still be able to reach "eligible" -- confirms they no longer gate
    # current eligibility.
    result = evaluate_eligibility(_pensionado_payload(), pathway="costa-rica-pensionado")
    assert result["eligibility_status"] == "eligible"


def test_costa_rica_pensionado_no_escape_choices_anywhere_in_schema():
    import json

    questions_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "costa_rica_pensionado"
        / "questions.json"
    )
    data = json.loads(questions_path.read_text(encoding="utf-8"))

    forbidden = {"not_sure", "not_ready", "unknown", "unsure", "maybe"}
    for field in data["taxonomy_fields"]:
        choices = field.get("choices") or []
        overlap = forbidden.intersection(choices)
        assert not overlap, f"{field['key']} has escape choice(s): {overlap}"


def test_spain_business_owner_below_2026_smi_threshold_returns_not_eligible():
    """Business Owner now uses the same 2026 SMI-based formula as Employee
    and Contractor."""
    result = evaluate_eligibility(
        _spain_payload(work_relationship="business_owner", monthly_income_eur="2441"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["business_owner_income_below_minimum"]


def test_spain_business_owner_at_2026_smi_threshold_is_eligible():
    result = evaluate_eligibility(
        _spain_payload(work_relationship="business_owner", monthly_income_eur="2442"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []


def test_spain_employee_below_2026_smi_threshold_returns_not_eligible():
    """200% of the 2026 SMI (EUR 1,221) = EUR 2,442/month for an individual
    Employee applicant."""
    result = evaluate_eligibility(
        _spain_payload(monthly_income_eur="2441"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["employee_income_below_minimum"]


def test_spain_employee_at_2026_smi_threshold_is_eligible():
    result = evaluate_eligibility(
        _spain_payload(monthly_income_eur="2442"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []


def test_spain_contractor_below_2026_smi_threshold_returns_not_eligible():
    """Contractor now uses the same 2026 SMI-based formula as Employee."""
    result = evaluate_eligibility(
        _spain_payload(work_relationship="contractor", monthly_income_eur="2441"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "not_eligible"
    assert result["failed_requirements"] == ["contractor_income_below_minimum"]


def test_spain_contractor_at_2026_smi_threshold_is_eligible():
    result = evaluate_eligibility(
        _spain_payload(work_relationship="contractor", monthly_income_eur="2442"),
        pathway="spain-dnv",
    )

    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []


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


def test_spain_employee_gets_only_its_role_income_fields():
    """Employee has its own dedicated applicant_type position (asked first,
    before the Employee-specific block) and its own dedicated
    employer-company-history/qualification questions -- it no longer uses
    the shared routing.supporting_company_operating_1_year question at all."""
    expected_keys = [
        "routing.applicant_type",
        "role.employee.employer_outside_spain",
        "role.employee.foreign_employment_months",
        "role.employee.remote_work_approved",
        "role.employee.employer_company_operating_1_year",
        "role.employee.qualification_or_experience",
        "role.employee.monthly_income_eur",
        "role.employee.income_evidence_types",
        "role.employee.income_evidence_months",
    ]
    answers = {
        "routing.applicant_type": "individual",
        "role.employee.employer_outside_spain": "yes",
        "role.employee.foreign_employment_months": "12",
        "role.employee.remote_work_approved": "yes",
        "role.employee.employer_company_operating_1_year": "yes",
        "role.employee.qualification_or_experience": "qualifying_education",
        "role.employee.monthly_income_eur": "2800",
        "role.employee.income_evidence_types": [
            "bank_statements",
            "employment_contract",
            "pay_stubs",
        ],
        "role.employee.income_evidence_months": "12_or_more",
    }

    payload = {"routing": {"work_relationship": "employee"}, "role": {}}
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
    assert result["next_field_key"] == "identity.nationality"
    assert "routing.supporting_company_operating_1_year" not in asked_keys
    assert all("income." not in key for key in asked_keys)


def test_spain_contractor_gets_only_its_role_income_fields():
    """Contractor has its own dedicated applicant_type position (asked
    first, before the Contractor-specific block), its own dedicated
    remote-work/company-history/qualification questions, and no longer asks
    the old service-agreements question at all."""
    expected_keys = [
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
    ]
    answers = {
        "routing.applicant_type": "individual",
        "role.contractor.monthly_income_eur": "2800",
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
    }

    payload = {"routing": {"work_relationship": "contractor"}, "role": {}}
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
    assert result["next_field_key"] == "identity.nationality"
    assert "role.contractor.service_agreements_available" not in asked_keys
    assert "routing.supporting_company_operating_1_year" not in asked_keys
    assert all("income." not in key for key in asked_keys)


def test_spain_business_owner_gets_only_its_role_income_fields():
    """Business Owner is ONE work type: no work_structure subrouting, its
    own dedicated applicant_type position (asked first), and its own
    dedicated business-location/duration/remote-operation/company-history/
    qualification questions."""
    expected_keys = [
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
    ]
    answers = {
        "routing.applicant_type": "individual",
        "role.business_owner.monthly_income_eur": "2800",
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
    }

    payload = {"routing": {"work_relationship": "business_owner"}, "role": {}}
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
    assert result["next_field_key"] == "identity.nationality"
    assert "role.business_owner.work_structure" not in asked_keys
    assert "routing.supporting_company_operating_1_year" not in asked_keys
    assert all("income." not in key for key in asked_keys)


def test_spain_valid_employee_contractor_and_business_owner_can_return_eligible():
    for work_relationship in ("employee", "contractor", "business_owner"):
        result = evaluate_eligibility(
            _spain_payload(work_relationship=work_relationship),
            pathway="spain-dnv",
        )

        assert result["eligibility_status"] == "eligible"
        assert result["failed_requirements"] == []


def test_spain_business_owner_is_one_work_type_with_its_own_checks():
    # Passing case.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
            business_outside_spain="yes",
            months_owned_operated="12",
            remote_operation_capable="yes",
            business_operating_1_year="yes",
            qualification_or_experience="qualifying_education",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "eligible"
    assert result["failed_requirements"] == []

    # Business based in Spain -> Business-Owner-specific hard failure code.
    result = evaluate_eligibility(
        _spain_payload(work_relationship="business_owner", business_outside_spain="no"),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert "business_owner_business_located_in_spain" in result["failed_requirements"]

    # Ownership/operation duration below 3 months.
    result = evaluate_eligibility(
        _spain_payload(work_relationship="business_owner", months_owned_operated="2"),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "business_owner_ownership_duration_below_minimum"
        in result["failed_requirements"]
    )

    # Remote operation not possible.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner", remote_operation_capable="no"
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "business_owner_remote_operation_not_possible"
        in result["failed_requirements"]
    )

    # Business operating history below 1 year (shared helper, own dotted key).
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner", business_operating_1_year="no"
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "supporting_company_operating_history_below_minimum"
        in result["failed_requirements"]
    )

    # Qualification/experience: "neither" hard-fails.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner", qualification_or_experience="neither"
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "business_owner_qualification_or_experience_not_met"
        in result["failed_requirements"]
    )

    # Spain-based activity at or below the 20% allowance is fine.
    result = evaluate_eligibility(
        _spain_payload(
            work_relationship="business_owner",
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
            spanish_clients_flag="yes",
            spanish_activity_percentage="21",
        ),
        pathway="spain-dnv",
    )
    assert result["eligibility_status"] == "not_eligible"
    assert (
        "business_owner_spanish_activity_above_threshold"
        in result["failed_requirements"]
    )


def test_spain_business_owner_has_no_work_structure_subrouting():
    """Business Owner is ONE work type -- there is no work_structure
    question, and no Employee-style or Contractor-style sub-branch."""
    payload = {"routing": {"work_relationship": "business_owner"}, "role": {}}
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "routing.applicant_type"

    import app.engine.pathways.spain_dnv.rules as spain_dnv_rules

    assert "business_owner_work_structure_needs_review" not in spain_dnv_rules.HARD_FAILURES
    source_text = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_dnv"
        / "rules.py"
    ).read_text(encoding="utf-8")
    assert '"role.business_owner.work_structure"' not in source_text
    assert "salary_as_employee" not in source_text
    assert "business_or_self_employment_income" not in source_text


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


def test_spain_contractor_no_longer_has_service_agreements_field_or_dependency():
    """The old vague 'ability to secure service agreements' question was
    removed from the live Contractor structure (per the approved Contractor
    review flow) -- it no longer appears in questions.json and no longer
    affects eligibility."""
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
    live_keys = {f["key"] for f in data["taxonomy_fields"]}
    assert "role.contractor.service_agreements_available" not in live_keys

    import app.engine.pathways.spain_dnv.rules as spain_dnv_rules

    assert "contractor_service_agreements_unavailable" not in spain_dnv_rules.HARD_FAILURES

    source_text = Path(
        Path(__file__).resolve().parents[1]
        / "app"
        / "engine"
        / "pathways"
        / "spain_dnv"
        / "rules.py"
    ).read_text(encoding="utf-8")
    assert '"role.contractor.service_agreements_available"' not in source_text

    # A payload without this field at all is still fully evaluable and eligible.
    result = evaluate_eligibility(
        _spain_payload(work_relationship="contractor"), pathway="spain-dnv"
    )
    assert result["eligibility_status"] == "eligible"


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
            income_history="less_than_3",
        ),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["meta"]["status"] == "needs_review"
    assert "manual review" in output["summary"].lower()
    assert output["next_steps"]["action"]["type"] == "email_followup"


def test_spain_not_eligible_uses_not_qualified_output():
    eligibility = evaluate_eligibility(
        _spain_payload(work_relationship="business_owner", monthly_income_eur="2441"),
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


def test_spain_business_owner_below_smi_threshold_includes_income_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(work_relationship="business_owner", monthly_income_eur="2441"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "business_owner_income_below_minimum"
    assert "200%" in output["clarifications"][0]["clarification"]


def test_spain_employee_below_smi_threshold_includes_employee_income_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(monthly_income_eur="2441"),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert output["clarifications"][0]["requirement"] == "employee_income_below_minimum"
    assert "200%" in output["clarifications"][0]["clarification"]


def test_spain_contractor_review_includes_qualification_clarification():
    eligibility = evaluate_eligibility(
        _spain_payload(
            work_relationship="contractor",
            qualification_or_experience="neither",
        ),
        pathway="spain-dnv",
    )
    output = build_output(eligibility)

    assert (
        output["clarifications"][0]["requirement"]
        == "contractor_qualification_or_experience_not_met"
    )
    assert "professional experience" in output["clarifications"][0]["clarification"]


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
    payload = {
        "routing": {"work_relationship": "employee", "applicant_type": "individual"}
    }
    result = evaluate(payload, pathway="spain-dnv")

    assert result["next_field_key"] == "role.employee.employer_outside_spain"
    assert result["next_field_key"] != "routing.service_interest"
    assert result["next_field_key"] != "role.profession_description"


def test_spain_numeric_income_question_has_no_band_choices():
    result = evaluate(
        {
            "routing": {"work_relationship": "employee", "applicant_type": "individual"},
            "role": {
                "employee": {
                    "employer_outside_spain": "yes",
                    "foreign_employment_months": "12",
                    "remote_work_approved": "yes",
                    "employer_company_operating_1_year": "yes",
                    "qualification_or_experience": "qualifying_education",
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


def test_spain_contractor_evidence_choices_and_duration_bands_render_exactly_as_approved():
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
    fields_by_key = {f["key"]: f for f in data["taxonomy_fields"]}

    evidence_field = fields_by_key["role.contractor.income_evidence_types"]
    assert evidence_field["label"] == "Which documents can you provide as proof of your contractor income?"
    assert evidence_field["choices"] == [
        "bank_statements",
        "service_agreements_or_contracts",
        "invoices",
        "other",
    ]

    duration_field = fields_by_key["role.contractor.income_evidence_months"]
    assert duration_field["label"] == "For how many months can you prove this income with those documents?"
    assert duration_field["choices"] == ["less_than_3", "3_to_5", "6_to_11", "12_or_more"]
    assert duration_field["input_type"] == "choice"

    qualification_field = fields_by_key["role.contractor.qualification_or_experience"]
    assert qualification_field["choices"] == [
        "qualifying_education",
        "3_or_more_years_of_relevant_professional_experience",
        "neither",
    ]


def test_spain_business_owner_evidence_choices_and_duration_bands_render_exactly_as_approved():
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
    fields_by_key = {f["key"]: f for f in data["taxonomy_fields"]}

    income_field = fields_by_key["role.business_owner.monthly_income_eur"]
    assert income_field["label"] == "What is your average gross monthly income from your business in EUR before tax?"
    assert income_field["input_type"] == "number"

    evidence_field = fields_by_key["role.business_owner.income_evidence_types"]
    assert evidence_field["label"] == "Which documents can you provide as proof of your business income?"
    assert evidence_field["choices"] == [
        "bank_statements",
        "business_registration",
        "tax_returns_or_financial_statements",
        "profit_loss_statements",
        "other",
    ]

    duration_field = fields_by_key["role.business_owner.income_evidence_months"]
    assert duration_field["label"] == "For how many months can you prove this income with those documents?"
    assert duration_field["choices"] == ["less_than_3", "3_to_5", "6_to_11", "12_or_more"]
    assert duration_field["input_type"] == "choice"

    qualification_field = fields_by_key["role.business_owner.qualification_or_experience"]
    assert qualification_field["choices"] == [
        "qualifying_education",
        "3_or_more_years_of_relevant_professional_experience",
        "neither",
    ]

    percentage_field = fields_by_key["role.business_owner.spanish_activity_percentage"]
    assert (
        percentage_field["label"]
        == "What percentage of your total professional work will be for clients or companies based in Spain?"
    )
    assert "business" not in percentage_field["label"].lower()


def test_spain_no_escape_choices_anywhere_in_schema():
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
