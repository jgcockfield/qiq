"""Portugal D7 Passive Income Visa eligibility rules.

Status-only logic for a passive-income / own-income residence pathway.
"""

from __future__ import annotations

from typing import Any, Dict, List


MINIMUM_MONTHLY_WAGE_EUR_2026 = 920
MAIN_APPLICANT_ANNUAL_INCOME_EUR = MINIMUM_MONTHLY_WAGE_EUR_2026 * 12
ADDITIONAL_ADULT_DEPENDENT_MULTIPLIER = 0.5
CHILD_DEPENDENT_MULTIPLIER = 0.3
MINIMUM_PASSPORT_VALIDITY_MONTHS = 3

VALID_PASSIVE_INCOME_SOURCE_TYPES = {
    "pension",
    "rental_property_income",
    "dividends",
    "royalties",
    "financial_investments",
    "intellectual_property",
    "savings_or_bank_balance",
}

VALID_INCOME_EVIDENCE_TYPES = {
    "bank_statements",
    "income_proof",
    "pension_proof",
    "investment_income_proof",
    "property_income_proof",
    "royalty_or_ip_income_proof",
}

VALID_ACCOMMODATION_STATUSES = {
    "lease_12_months_or_more",
    "property_deed",
    "other_qualifying_accommodation",
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
    "active_employment_or_non_passive_intent",
    "employment_or_active_work_income_not_accepted",
    "false_statement_risk_not_acknowledged",
    "health_travel_insurance_unavailable",
    "income_not_available_in_portugal",
    "insufficient_passive_income",
    "lawful_residence_where_applying_unavailable",
    "passport_validity_below_minimum",
    "police_clearance_unavailable",
    "portugal_accommodation_12_months_unavailable",
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


def _required_annual_income(
    additional_adult_dependents_count: int,
    child_or_dependent_non_minor_count: int,
) -> float:
    adult_dependent_amount = (
        MAIN_APPLICANT_ANNUAL_INCOME_EUR
        * ADDITIONAL_ADULT_DEPENDENT_MULTIPLIER
        * additional_adult_dependents_count
    )
    child_dependent_amount = (
        MAIN_APPLICANT_ANNUAL_INCOME_EUR
        * CHILD_DEPENDENT_MULTIPLIER
        * child_or_dependent_non_minor_count
    )
    return (
        MAIN_APPLICANT_ANNUAL_INCOME_EUR
        + adult_dependent_amount
        + child_dependent_amount
    )


def _evaluate_applicant_route(
    payload: Dict[str, Any],
    failed: List[str],
    routing: Dict[str, Any],
) -> tuple[int, int]:
    applicant_type = _get_dotted(payload, "routing.applicant_type")
    routing["applicant_type"] = applicant_type

    if applicant_type not in {"individual", "family"}:
        failed.append("applicant_type_missing")
        return 0, 0

    if applicant_type == "individual":
        return 0, 0

    dependents_count = _as_int(_get_dotted(payload, "routing.dependents_count"))
    additional_adult_count = _as_int(
        _get_dotted(payload, "routing.additional_adult_dependents_count")
    )
    child_or_dependent_non_minor_count = _as_int(
        _get_dotted(payload, "routing.child_or_dependent_non_minor_count")
    )

    if dependents_count is None or dependents_count < 1:
        failed.append("dependents_count_missing")
        dependents_count = 0
    if additional_adult_count is None or additional_adult_count < 0:
        failed.append("additional_adult_dependents_count_missing")
        additional_adult_count = 0
    if child_or_dependent_non_minor_count is None or child_or_dependent_non_minor_count < 0:
        failed.append("child_or_dependent_non_minor_count_missing")
        child_or_dependent_non_minor_count = 0

    if (
        dependents_count
        and additional_adult_count + child_or_dependent_non_minor_count
        != dependents_count
    ):
        failed.append("dependent_count_mismatch_needs_review")

    if not _get_dotted(payload, "routing.dependent_relationships"):
        failed.append("dependent_relationships_missing")

    family_documents = _get_dotted(payload, "routing.family_documents_available")
    if _is_no(family_documents):
        failed.append("family_documents_needs_review")
    elif not _is_yes(family_documents):
        failed.append("family_documents_needs_review")

    return additional_adult_count, child_or_dependent_non_minor_count


def _evaluate_route_intent_and_lawful_status(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
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

    passive_income_intent = _get_dotted(payload, "routing.passive_own_income_intent")
    if _is_no(passive_income_intent):
        failed.append("active_employment_or_non_passive_intent")
    elif not _is_yes(passive_income_intent):
        failed.append("passive_own_income_intent_needs_review")


def _evaluate_financials(
    payload: Dict[str, Any],
    failed: List[str],
    required_annual_income: float,
) -> None:
    annual_income = _as_float(
        _get_dotted(payload, "financial.annual_passive_income_eur")
    )
    if annual_income is None:
        failed.append("annual_passive_income_missing_or_unrecognized")
    elif annual_income < required_annual_income:
        failed.append("insufficient_passive_income")

    income_sources = set(_as_values(_get_dotted(payload, "financial.income_source_types")))
    if "employment_or_active_work_income" in income_sources:
        failed.append("employment_or_active_work_income_not_accepted")
    if not income_sources.intersection(VALID_PASSIVE_INCOME_SOURCE_TYPES):
        failed.append("passive_income_source_needs_review")

    income_evidence = set(
        _as_values(_get_dotted(payload, "financial.income_evidence_types"))
    )
    if not income_evidence.intersection(VALID_INCOME_EVIDENCE_TYPES):
        failed.append("income_evidence_needs_review")

    portuguese_bank_availability = _get_dotted(
        payload,
        "financial.portuguese_bank_availability",
    )
    if portuguese_bank_availability == "no":
        failed.append("income_not_available_in_portugal")
    elif portuguese_bank_availability != "yes":
        failed.append("portuguese_bank_availability_needs_review")


def _evaluate_accommodation_passport_and_insurance(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    accommodation = _get_dotted(
        payload,
        "housing.portugal_accommodation_12_months",
    )
    if accommodation in {"less_than_12_months", "not_available"}:
        failed.append("portugal_accommodation_12_months_unavailable")
    elif accommodation not in VALID_ACCOMMODATION_STATUSES:
        failed.append("portugal_accommodation_12_months_needs_review")

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


def _evaluate_background_and_compliance(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
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

    aima_acknowledged = _get_dotted(
        payload,
        "compliance.aima_residence_step_acknowledged",
    )
    if not _is_yes(aima_acknowledged):
        failed.append("aima_residence_step_needs_review")

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
        failed.append("false_statement_risk_not_acknowledged")
    elif not _is_yes(truthful_documents_acknowledged):
        failed.append("truthful_documents_needs_review")


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    additional_adult_count, child_or_dependent_non_minor_count = (
        _evaluate_applicant_route(payload, failed, routing)
    )
    required_annual_income = _required_annual_income(
        additional_adult_count,
        child_or_dependent_non_minor_count,
    )

    _evaluate_route_intent_and_lawful_status(payload, failed)
    _evaluate_financials(payload, failed, required_annual_income)
    _evaluate_accommodation_passport_and_insurance(payload, failed)
    _evaluate_background_and_compliance(payload, failed)

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
        "pathway": "portugal_d7",
        "work_type": "passive_own_income",
        "visa_type": "Portugal D7 Passive Income Visa",
        "minimum_annual_main_applicant_income_eur": MAIN_APPLICANT_ANNUAL_INCOME_EUR,
        "required_annual_passive_income_eur": required_annual_income,
        "dependent_income_formula": {
            "main_applicant": "100%",
            "additional_adult": "50%",
            "child_or_dependent_non_minor": "30%",
        },
    }
