"""Portugal Digital Nomad Visa eligibility rules.

Status-only logic for Portugal's remote-work / digital-nomad pathway.
This is not Portugal D7 passive-income logic.
"""

from __future__ import annotations

from typing import Any, Dict, List


MINIMUM_MONTHLY_WAGE_EUR_2026 = 920
REMOTE_WORK_INCOME_MULTIPLIER = 4
MINIMUM_AVERAGE_MONTHLY_INCOME_EUR = (
    MINIMUM_MONTHLY_WAGE_EUR_2026 * REMOTE_WORK_INCOME_MULTIPLIER
)
MINIMUM_PASSPORT_VALIDITY_MONTHS = 3

VALID_VISA_ROUTES = {
    "residence_visa",
    "temporary_stay_under_1_year",
}

VALID_WORK_RELATIONSHIPS = {
    "remote_employee",
    "freelancer_independent",
    "business_owner_company_service",
}

VALID_INCOME_EVIDENCE_TYPES = {
    "payslips",
    "invoices",
    "contracts",
    "bank_statements",
    "income_proof",
}

VALID_INSURANCE_STATUSES = {
    "have_it",
    "bilateral_exception_applies",
}

VALID_POLICE_CLEARANCE_STATUSES = {
    "yes",
    "under_16_exempt",
}

HARD_FAILURES = {
    "business_owner_company_service_documents_unavailable",
    "employee_contract_or_declaration_unavailable",
    "family_stable_means_unavailable",
    "health_travel_insurance_unavailable",
    "income_below_minimum",
    "independent_service_or_client_proof_unavailable",
    "lawful_residence_where_applying_unavailable",
    "passport_validity_below_minimum",
    "police_clearance_unavailable",
    "remote_work_not_for_entities_outside_portugal",
    "removal_or_refusal_alert",
    "settlement_statement_unavailable",
    "tax_residence_certificate_unavailable",
    "truthful_documents_not_acknowledged",
}


def _get_dotted(payload: Dict[str, Any], dotted_key: str) -> Any:
    current: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _as_float(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _is_yes(value: Any) -> bool:
    return value == "yes" or value is True


def _is_no(value: Any) -> bool:
    return value == "no" or value is False


def _evaluate_visa_route(
    payload: Dict[str, Any],
    failed: List[str],
    routing: Dict[str, Any],
) -> str | None:
    visa_route = _get_dotted(payload, "routing.visa_route")
    routing["visa_route"] = visa_route

    if visa_route not in VALID_VISA_ROUTES:
        failed.append("visa_route_needs_review")
        return None

    return visa_route


def _evaluate_work_route(
    payload: Dict[str, Any],
    failed: List[str],
    routing: Dict[str, Any],
) -> str | None:
    work_relationship = _get_dotted(payload, "routing.work_relationship")
    routing["work_relationship"] = work_relationship

    if work_relationship not in VALID_WORK_RELATIONSHIPS:
        failed.append("work_relationship_missing_or_unrecognized")
        return None

    outside_portugal = _get_dotted(payload, "work.entities_outside_portugal")
    if _is_no(outside_portugal):
        failed.append("remote_work_not_for_entities_outside_portugal")
    elif not _is_yes(outside_portugal):
        failed.append("remote_work_entities_outside_portugal_needs_review")

    if work_relationship == "remote_employee":
        contract_or_declaration = _get_dotted(
            payload,
            "role.employee.contract_or_declaration_available",
        )
        if _is_no(contract_or_declaration):
            failed.append("employee_contract_or_declaration_unavailable")
        elif not _is_yes(contract_or_declaration):
            failed.append("employee_contract_or_declaration_needs_review")

    if work_relationship == "freelancer_independent":
        service_or_client_proof = _get_dotted(
            payload,
            "role.independent.service_or_client_proof_available",
        )
        if _is_no(service_or_client_proof):
            failed.append("independent_service_or_client_proof_unavailable")
        elif not _is_yes(service_or_client_proof):
            failed.append("independent_service_or_client_proof_needs_review")

    if work_relationship == "business_owner_company_service":
        company_service_documents = _get_dotted(
            payload,
            "role.business_owner.company_service_documents_available",
        )
        if _is_no(company_service_documents):
            failed.append("business_owner_company_service_documents_unavailable")
        elif not _is_yes(company_service_documents):
            failed.append("business_owner_company_service_documents_needs_review")

    return work_relationship


def _evaluate_financials(payload: Dict[str, Any], failed: List[str]) -> None:
    average_monthly_income = _as_float(
        _get_dotted(
            payload,
            "financial.average_monthly_income_last_3_months_eur",
        )
    )
    if average_monthly_income is None:
        failed.append("average_monthly_income_missing_or_unrecognized")
    elif average_monthly_income < MINIMUM_AVERAGE_MONTHLY_INCOME_EUR:
        failed.append("income_below_minimum")

    income_evidence = set(
        _as_values(_get_dotted(payload, "financial.income_evidence_types"))
    )
    if not income_evidence.intersection(VALID_INCOME_EVIDENCE_TYPES):
        failed.append("income_evidence_needs_review")

    tax_residence_certificate = _get_dotted(
        payload,
        "documents.tax_residence_certificate_available",
    )
    if _is_no(tax_residence_certificate):
        failed.append("tax_residence_certificate_unavailable")
    elif not _is_yes(tax_residence_certificate):
        failed.append("tax_residence_certificate_needs_review")


def _evaluate_applicant_route(
    payload: Dict[str, Any],
    failed: List[str],
    routing: Dict[str, Any],
) -> None:
    applicant_type = _get_dotted(payload, "routing.applicant_type")
    routing["applicant_type"] = applicant_type

    if applicant_type not in {"individual", "family"}:
        failed.append("applicant_type_missing")
        return

    if applicant_type == "individual":
        return

    dependents_count = _as_int(_get_dotted(payload, "routing.dependents_count"))
    if dependents_count is None or dependents_count < 1:
        failed.append("dependents_count_missing")

    if not _get_dotted(payload, "routing.dependent_relationships"):
        failed.append("dependent_relationships_missing")

    family_documents = _get_dotted(payload, "routing.family_documents_available")
    if not _is_yes(family_documents):
        failed.append("family_documents_needs_review")

    family_stable_means = _get_dotted(
        payload,
        "financial.family_stable_means_available",
    )
    if _is_no(family_stable_means):
        failed.append("family_stable_means_unavailable")
    elif not _is_yes(family_stable_means):
        failed.append("family_stable_means_needs_review")


def _evaluate_lawful_status(payload: Dict[str, Any], failed: List[str]) -> None:
    matches_nationality_country = _get_dotted(
        payload,
        "routing.application_country_matches_nationality",
    )

    if matches_nationality_country == "no":
        lawful_residence = _get_dotted(
            payload,
            "routing.lawful_residence_where_applying",
        )
        if _is_no(lawful_residence):
            failed.append("lawful_residence_where_applying_unavailable")
        elif not _is_yes(lawful_residence):
            failed.append("lawful_residence_where_applying_needs_review")
    elif matches_nationality_country != "yes":
        failed.append("application_country_needs_review")


def _evaluate_documents_background_and_housing(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if passport_months is None:
        failed.append("passport_validity_missing_or_unrecognized")
    elif passport_months < MINIMUM_PASSPORT_VALIDITY_MONTHS:
        failed.append("passport_validity_below_minimum")

    insurance_status = _get_dotted(payload, "routing.health_travel_insurance_status")
    if insurance_status == "cannot_obtain":
        failed.append("health_travel_insurance_unavailable")
    elif insurance_status not in VALID_INSURANCE_STATUSES:
        failed.append("health_travel_insurance_needs_review")

    police_clearance = _get_dotted(payload, "routing.police_clearance_available")
    if police_clearance == "no":
        failed.append("police_clearance_unavailable")
    elif police_clearance not in VALID_POLICE_CLEARANCE_STATUSES:
        failed.append("police_clearance_needs_review")

    criminal_record = _get_dotted(payload, "routing.criminal_record_flag")
    if criminal_record == "yes":
        failed.append("criminal_record_needs_review")
    elif criminal_record != "no":
        failed.append("criminal_record_needs_review")

    removal_or_refusal_alert = _get_dotted(
        payload,
        "routing.removal_or_refusal_alert_flag",
    )
    if removal_or_refusal_alert == "yes":
        failed.append("removal_or_refusal_alert")
    elif removal_or_refusal_alert != "no":
        failed.append("removal_or_refusal_alert_needs_review")

    settlement_statement = _get_dotted(payload, "housing.settlement_statement_ready")
    if _is_no(settlement_statement):
        failed.append("settlement_statement_unavailable")
    elif not _is_yes(settlement_statement):
        failed.append("settlement_statement_needs_review")


def _evaluate_compliance(
    payload: Dict[str, Any],
    failed: List[str],
    visa_route: str | None,
) -> None:
    if visa_route == "residence_visa":
        aima_acknowledged = _get_dotted(
            payload,
            "compliance.aima_residence_permit_acknowledged",
        )
        if not _is_yes(aima_acknowledged):
            failed.append("aima_residence_permit_acknowledgement_needs_review")

        renewal_acknowledged = _get_dotted(
            payload,
            "compliance.renewal_acknowledged",
        )
        if not _is_yes(renewal_acknowledged):
            failed.append("renewal_acknowledgement_needs_review")

    extra_documents_acknowledged = _get_dotted(
        payload,
        "consulate.discretion_extra_documents_acknowledged",
    )
    if not _is_yes(extra_documents_acknowledged):
        failed.append("discretionary_extra_documents_needs_review")

    truthful_documents_acknowledged = _get_dotted(
        payload,
        "compliance.truthful_documents_acknowledged",
    )
    if _is_no(truthful_documents_acknowledged):
        failed.append("truthful_documents_not_acknowledged")
    elif not _is_yes(truthful_documents_acknowledged):
        failed.append("truthful_documents_needs_review")


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    visa_route = _evaluate_visa_route(payload, failed, routing)
    work_relationship = _evaluate_work_route(payload, failed, routing)
    _evaluate_financials(payload, failed)
    _evaluate_applicant_route(payload, failed, routing)
    _evaluate_lawful_status(payload, failed)
    _evaluate_documents_background_and_housing(payload, failed)
    _evaluate_compliance(payload, failed, visa_route)

    if any(requirement in HARD_FAILURES for requirement in failed):
        status = "not_eligible"
    elif failed:
        status = "needs_review"
    else:
        status = "eligible"

    return {
        "eligibility_status": status,
        "failed_requirements": failed,
        "routing": routing,
        "pathway": "portugal_dnv",
        "work_type": work_relationship,
        "visa_type": "Portugal Digital Nomad Visa",
        "minimum_average_monthly_income_eur": MINIMUM_AVERAGE_MONTHLY_INCOME_EUR,
        "income_threshold_formula": "4 x 2026 Portuguese minimum wage",
    }
