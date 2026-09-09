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
MINIMUM_BACKGROUND_CHECK_AGE = 16

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

VALID_INSURANCE_STATUSES = {
    "have_it",
    "bilateral_exception_applies",
}

# NOTE: routing.passive_own_income_intent (a standalone self-declaration),
# financial.portuguese_bank_availability, routing.family_documents_available,
# and compliance.truthful_documents_acknowledged were removed from the live
# eligibility flow (and from this module) per the approved canonical
# Markdown (questions_d7.md). Their former requirement codes
# (active_employment_or_non_passive_intent, passive_own_income_intent_needs_review,
# income_not_available_in_portugal, portuguese_bank_availability_needs_review,
# family_documents_needs_review, false_statement_risk_not_acknowledged,
# truthful_documents_needs_review) are no longer emitted anywhere. See
# clarifications.json/output.json for what was cleaned up alongside them, and
# the MoveWise Review Notes for the open legal questions this removal raises.
#
# The substantive "must not be supported by active employment income" rule is
# preserved unchanged -- it now relies solely on whether the applicant
# selects "employment_or_active_work_income" in financial.income_source_types
# (see _evaluate_financials below), which was already an independent,
# unmodified check.
HARD_FAILURES = {
    "employment_or_active_work_income_not_accepted",
    "health_travel_insurance_unavailable",
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

    return additional_adult_count, child_or_dependent_non_minor_count


def _evaluate_application_country_and_lawful_status(
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


def _evaluate_accommodation_passport_and_insurance(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    accommodation = _get_dotted(
        payload,
        "housing.portugal_accommodation_12_months",
    )
    if accommodation == "no":
        failed.append("portugal_accommodation_12_months_unavailable")
    elif accommodation != "have_it":
        # Covers "will_arrange" and any missing/unrecognized value.
        failed.append("portugal_accommodation_needs_review")

    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if passport_months is None:
        failed.append("passport_validity_missing_or_unrecognized")
    elif passport_months < MINIMUM_PASSPORT_VALIDITY_MONTHS:
        failed.append("passport_validity_below_minimum")

    insurance_status = _get_dotted(payload, "routing.health_travel_insurance_status")
    if insurance_status == "no":
        failed.append("health_travel_insurance_unavailable")
    elif insurance_status not in VALID_INSURANCE_STATUSES:
        # Covers "will_obtain" and any missing/unrecognized value -- preserved
        # exactly as before; whether "will_obtain" should ultimately pass is
        # an open MoveWise item, not decided by this migration.
        failed.append("health_travel_insurance_needs_review")


def _evaluate_background(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    # Portugal D7's criminal-record-certificate requirement does not apply
    # under age 16 (the live flow's former "under_16_exempt" choice). The
    # background questions are only asked (see questions.json's applies_when)
    # when identity.age >= 16, so a missing answer here for an applicant
    # under 16 must NOT be treated as needs_review -- it's the same pass
    # state the old exemption choice produced. If age itself can't be
    # parsed, fall through and evaluate normally rather than silently
    # exempting an applicant of unknown age.
    age = _as_int(_get_dotted(payload, "identity.age"))
    if age is not None and age < MINIMUM_BACKGROUND_CHECK_AGE:
        return

    police_clearance = _get_dotted(payload, "routing.police_clearance_available")
    if _is_no(police_clearance):
        failed.append("police_clearance_unavailable")
    elif not _is_yes(police_clearance):
        failed.append("police_clearance_needs_review")

    criminal_record = _get_dotted(payload, "routing.criminal_record_flag")
    if criminal_record == "yes":
        failed.append("criminal_record_needs_review")
    elif criminal_record != "no":
        failed.append("criminal_record_needs_review")


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

    _evaluate_application_country_and_lawful_status(payload, failed)
    _evaluate_financials(payload, failed, required_annual_income)
    _evaluate_accommodation_passport_and_insurance(payload, failed)
    _evaluate_background(payload, failed)

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
