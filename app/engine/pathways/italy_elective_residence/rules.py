"""Italy Elective Residence Visa eligibility rules.

Status-only logic for a passive-income / no-work residence pathway.
"""

from __future__ import annotations

from typing import Any, Dict, List


MINIMUM_ANNUAL_PASSIVE_INCOME_EUR = 31000
MINIMUM_PASSPORT_VALIDITY_MONTHS = 3
SAN_FRANCISCO_PASSPORT_VALIDITY_MONTHS = 15
MINIMUM_BLANK_PASSPORT_PAGES = 2

VALID_INCOME_SOURCE_TYPES = {
    "pension",
    "social_security",
    "annuities",
    "rental_property",
    "securities_or_investments",
    "trusts",
    "stable_commercial_activity",
}

VALID_INCOME_EVIDENCE_TYPES = {
    "bank_letters",
    "financial_adviser_letters",
    "pension_or_social_security_letters",
    "investment_statements",
    "tax_returns",
    "property_or_rental_income_documents",
}

VALID_LODGING_STATUSES = {
    "registered_lease",
    "rental_contract",
    "property_deed",
}

HARD_FAILURES = {
    "adult_child_dependency_not_met",
    "employment_or_work_income_not_accepted",
    "extended_tourism_purpose",
    "fbi_background_unavailable",
    "health_insurance_unavailable",
    "insufficient_passive_income",
    "no_work_in_italy_not_confirmed",
    "passport_blank_pages_below_minimum",
    "passport_issued_too_old_for_paris",
    "passport_validity_below_minimum",
    "permesso_acknowledgement_missing",
    "qualifying_italian_lodging_unavailable",
    "renewal_acknowledgement_missing",
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


def _required_annual_income(dependents_count: int) -> int:
    return MINIMUM_ANNUAL_PASSIVE_INCOME_EUR * (1 + dependents_count)


def _evaluate_applicant_route(
    payload: Dict[str, Any],
    failed: List[str],
    routing: Dict[str, Any],
) -> int:
    applicant_type = _get_dotted(payload, "routing.applicant_type")
    routing["applicant_type"] = applicant_type

    if applicant_type not in {"individual", "family"}:
        failed.append("applicant_type_missing")
        return 0

    if applicant_type == "individual":
        return 0

    dependents_count = _as_int(_get_dotted(payload, "routing.dependents_count"))
    if dependents_count is None or dependents_count < 1:
        failed.append("dependents_count_missing")
        dependents_count = 0

    if not _get_dotted(payload, "routing.dependent_relationships"):
        failed.append("dependent_relationships_missing")

    adult_children_status = _get_dotted(
        payload,
        "routing.dependent_adult_children_living_with_parents",
    )
    if adult_children_status == "no":
        failed.append("adult_child_dependency_not_met")
    elif adult_children_status not in {"no_adult_children", "yes"}:
        failed.append("adult_child_dependency_needs_review")

    family_documents = _get_dotted(payload, "routing.family_documents_available")
    if _is_no(family_documents):
        failed.append("family_documents_needs_review")
    elif not _is_yes(family_documents):
        failed.append("family_documents_needs_review")

    return dependents_count


def _evaluate_route_intent(payload: Dict[str, Any], failed: List[str]) -> None:
    consulate_jurisdiction = _get_dotted(payload, "routing.consulate_jurisdiction")
    if consulate_jurisdiction in {None, "", "not_sure", "other"}:
        failed.append("consulate_jurisdiction_needs_review")

    no_work_acknowledged = _get_dotted(
        payload,
        "routing.no_work_in_italy_acknowledged",
    )
    if _is_no(no_work_acknowledged):
        failed.append("no_work_in_italy_not_confirmed")
    elif not _is_yes(no_work_acknowledged):
        failed.append("no_work_in_italy_needs_review")

    residence_intent = _get_dotted(payload, "routing.stable_residence_intent")
    if residence_intent == "extended_tourism":
        failed.append("extended_tourism_purpose")
    elif residence_intent != "stable_residence":
        failed.append("stable_residence_intent_needs_review")


def _evaluate_financials(
    payload: Dict[str, Any],
    failed: List[str],
    required_annual_income: int,
) -> None:
    annual_passive_income = _as_float(
        _get_dotted(payload, "financial.annual_passive_income_eur")
    )
    if annual_passive_income is None:
        failed.append("passive_income_missing_or_unrecognized")
    elif annual_passive_income < required_annual_income:
        failed.append("insufficient_passive_income")
    elif annual_passive_income == required_annual_income:
        failed.append("passive_income_at_reference_threshold_needs_review")

    available_assets = _as_float(_get_dotted(payload, "financial.available_assets_eur"))
    if available_assets is None or available_assets <= 0:
        failed.append("financial_assets_need_review")

    income_sources = set(_as_values(_get_dotted(payload, "financial.income_source_types")))
    if "employment_or_work_income" in income_sources:
        failed.append("employment_or_work_income_not_accepted")
    if not income_sources.intersection(VALID_INCOME_SOURCE_TYPES):
        failed.append("passive_income_source_needs_review")

    income_evidence = set(
        _as_values(_get_dotted(payload, "financial.income_evidence_types"))
    )
    if not income_evidence.intersection(VALID_INCOME_EVIDENCE_TYPES):
        failed.append("income_evidence_needs_review")

    tax_returns_available = _get_dotted(payload, "financial.tax_returns_available")
    if tax_returns_available == "less_than_two_years":
        failed.append("tax_returns_need_review")
    elif tax_returns_available == "two_years_basic_returns_only":
        failed.append("tax_returns_complete_schedules_need_review")
    elif tax_returns_available != "two_years_complete_with_schedules":
        failed.append("tax_returns_need_review")


def _evaluate_lodging_insurance_and_passport(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    lodging_status = _get_dotted(payload, "housing.italy_lodging_status")
    if lodging_status == "not_available":
        failed.append("qualifying_italian_lodging_unavailable")
    elif lodging_status == "hotel_or_short_term_bookings":
        failed.append("lodging_hotels_or_short_term_bookings_need_review")
    elif lodging_status not in VALID_LODGING_STATUSES:
        failed.append("qualifying_italian_lodging_needs_review")

    health_insurance_status = _get_dotted(payload, "routing.health_insurance_status")
    if health_insurance_status == "cannot_obtain":
        failed.append("health_insurance_unavailable")
    elif health_insurance_status != "have_it":
        failed.append("health_insurance_needs_review")

    coverage_level = _get_dotted(payload, "routing.health_insurance_coverage_level")
    if coverage_level != "meets_consular_coverage":
        failed.append("health_insurance_coverage_needs_review")

    consulate_jurisdiction = _get_dotted(payload, "routing.consulate_jurisdiction")
    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if passport_months is None:
        failed.append("passport_validity_missing_or_unrecognized")
    elif passport_months < MINIMUM_PASSPORT_VALIDITY_MONTHS:
        failed.append("passport_validity_below_minimum")
    elif (
        consulate_jurisdiction == "san_francisco"
        and passport_months < SAN_FRANCISCO_PASSPORT_VALIDITY_MONTHS
    ):
        failed.append("passport_validity_san_francisco_threshold_needs_review")

    passport_issued_within_10_years = _get_dotted(
        payload,
        "routing.passport_issued_within_10_years",
    )
    if _is_no(passport_issued_within_10_years):
        if consulate_jurisdiction == "paris":
            failed.append("passport_issued_too_old_for_paris")
        else:
            failed.append("passport_issue_date_needs_review")
    elif not _is_yes(passport_issued_within_10_years):
        failed.append("passport_issue_date_needs_review")

    blank_pages = _as_int(_get_dotted(payload, "routing.passport_blank_pages"))
    if blank_pages is None:
        failed.append("passport_blank_pages_missing_or_unrecognized")
    elif blank_pages < MINIMUM_BLANK_PASSPORT_PAGES:
        if consulate_jurisdiction == "paris":
            failed.append("passport_blank_pages_below_minimum")
        else:
            failed.append("passport_blank_pages_need_review")


def _evaluate_background_and_compliance(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    consulate_jurisdiction = _get_dotted(payload, "routing.consulate_jurisdiction")
    if consulate_jurisdiction == "san_francisco":
        fbi_summary_available = _get_dotted(
            payload,
            "background.fbi_identity_history_available",
        )
        if _is_no(fbi_summary_available):
            failed.append("fbi_background_unavailable")
        elif not _is_yes(fbi_summary_available):
            failed.append("fbi_background_needs_review")

    permesso_acknowledged = _get_dotted(
        payload,
        "compliance.permesso_8_day_acknowledged",
    )
    if _is_no(permesso_acknowledged):
        failed.append("permesso_acknowledgement_missing")
    elif not _is_yes(permesso_acknowledged):
        failed.append("permesso_acknowledgement_needs_review")

    renewal_acknowledged = _get_dotted(
        payload,
        "compliance.annual_renewal_acknowledged",
    )
    if _is_no(renewal_acknowledged):
        failed.append("renewal_acknowledgement_missing")
    elif not _is_yes(renewal_acknowledged):
        failed.append("renewal_acknowledgement_needs_review")

    extra_documents_acknowledged = _get_dotted(
        payload,
        "consulate.additional_documents_acknowledged",
    )
    if not _is_yes(extra_documents_acknowledged):
        failed.append("consulate_discretion_extra_documents_needs_review")


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    dependents_count = _evaluate_applicant_route(payload, failed, routing)
    required_annual_income = _required_annual_income(dependents_count)

    _evaluate_route_intent(payload, failed)
    _evaluate_financials(payload, failed, required_annual_income)
    _evaluate_lodging_insurance_and_passport(payload, failed)
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
        "pathway": "italy_elective_residence",
        "work_type": "passive_income_no_work",
        "visa_type": "Italy Elective Residence Visa",
        "minimum_annual_passive_income_eur": MINIMUM_ANNUAL_PASSIVE_INCOME_EUR,
        "required_annual_passive_income_eur": required_annual_income,
    }
