"""Italy Elective Residence Visa eligibility rules.

Status-only logic for a passive-income / no-work residence pathway.
"""

from __future__ import annotations

from typing import Any, Dict, List


MINIMUM_ANNUAL_PASSIVE_INCOME_EUR = 31000
MINIMUM_PASSPORT_VALIDITY_MONTHS = 3
SAN_FRANCISCO_PASSPORT_VALIDITY_MONTHS = 15

VALID_CONSULATE_JURISDICTIONS = {
    "new_york",
    "chicago",
    "san_francisco",
    "boston",
    "los_angeles",
    "paris",
    "other",
}

VALID_INCOME_SOURCE_TYPES = {
    "pension",
    "social_security",
    "annuities",
    "rental_property",
    "securities_or_investments",
    "trusts",
    "stable_commercial_activity",
}

VALID_LODGING_STATUSES = {
    "registered_lease",
    "rental_contract",
    "property_deed",
}

# NOTE: the following live questions/codes were removed during the canonical
# cleanup (questions_elective_residence.md):
#   identity.nationality -- never evaluated; no eligibility consequence.
#   financial.income_evidence_types (income_evidence_needs_review) --
#     document-evidence readiness, not an initial eligibility fact.
#   financial.tax_returns_available (tax_returns_need_review /
#     tax_returns_complete_schedules_need_review) -- document-evidence
#     readiness; tax-return readiness belongs downstream.
#   routing.family_documents_available (family_documents_needs_review) --
#     document-evidence readiness; the substantive family-relationship fact
#     remains represented by routing.dependent_relationships.
#   routing.health_insurance_coverage_level
#     (health_insurance_coverage_needs_review) -- folded into the single
#     canonical routing.health_insurance_status Yes/No fact.
#   routing.passport_blank_pages (passport_blank_pages_below_minimum /
#     _need_review / _missing_or_unrecognized) -- moved to
#     questions.json's post_eligibility_checklist as a Paris-specific
#     application-preparation item; no longer a live eligibility fact.
#   background.fbi_identity_history_available (fbi_background_unavailable /
#     _needs_review) -- moved to questions.json's post_eligibility_checklist
#     as a San-Francisco-specific application-preparation item; no longer a
#     live eligibility fact.
#   compliance.permesso_8_day_acknowledged and
#   compliance.annual_renewal_acknowledged (permesso_acknowledgement_missing /
#     _needs_review, renewal_acknowledgement_missing / _needs_review) --
#     moved to questions.json's post_eligibility_checklist. These were
#     previously frozen live/hard-fail-capable pending legal review; the
#     canonical redesign explicitly overrides that freeze and relocates both
#     to post-entry compliance, matching every other pathway audited this
#     session. See the MoveWise Review Notes in the implementation report.
#
# The previous 100%-per-dependent income multiplier
# (MINIMUM_ANNUAL_PASSIVE_INCOME_EUR * (1 + dependents_count)) was also
# removed: it was not sourced from requirements_reference.md, and
# routing.dependents_count no longer affects the numeric income threshold.
# It remains a collected family fact pending a legally confirmed family
# financial formula.
HARD_FAILURES = {
    "adult_child_dependency_not_met",
    "employment_or_work_income_not_accepted",
    "extended_tourism_purpose",
    "health_insurance_unavailable",
    "insufficient_passive_income",
    "no_work_in_italy_not_confirmed",
    "passport_issued_too_old_for_paris",
    "passport_validity_below_minimum",
    "qualifying_italian_lodging_unavailable",
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
    routing["dependents_count"] = dependents_count
    if dependents_count is None or dependents_count < 1:
        failed.append("dependents_count_missing")

    relationships = set(_as_values(_get_dotted(payload, "routing.dependent_relationships")))
    if not relationships:
        failed.append("dependent_relationships_missing")

    if "adult_child" in relationships:
        adult_children_status = _get_dotted(
            payload,
            "routing.dependent_adult_children_living_with_parents",
        )
        if _is_no(adult_children_status):
            failed.append("adult_child_dependency_not_met")
        elif not _is_yes(adult_children_status):
            failed.append("adult_child_dependency_needs_review")


def _evaluate_route_intent(payload: Dict[str, Any], failed: List[str]) -> None:
    consulate_jurisdiction = _get_dotted(payload, "routing.consulate_jurisdiction")
    if consulate_jurisdiction not in VALID_CONSULATE_JURISDICTIONS or consulate_jurisdiction == "other":
        failed.append("consulate_jurisdiction_needs_review")

    intends_to_work = _get_dotted(payload, "work.intends_to_work_in_italy")
    if _is_yes(intends_to_work):
        failed.append("no_work_in_italy_not_confirmed")
    elif not _is_no(intends_to_work):
        failed.append("no_work_in_italy_needs_review")

    residence_intent = _get_dotted(payload, "routing.stable_residence_intent")
    if _is_no(residence_intent):
        failed.append("extended_tourism_purpose")
    elif not _is_yes(residence_intent):
        failed.append("stable_residence_intent_needs_review")


def _evaluate_financials(payload: Dict[str, Any], failed: List[str]) -> None:
    annual_passive_income = _as_float(
        _get_dotted(payload, "financial.annual_passive_income_eur")
    )
    if annual_passive_income is None:
        failed.append("passive_income_missing_or_unrecognized")
    elif annual_passive_income < MINIMUM_ANNUAL_PASSIVE_INCOME_EUR:
        failed.append("insufficient_passive_income")
    elif annual_passive_income == MINIMUM_ANNUAL_PASSIVE_INCOME_EUR:
        failed.append("passive_income_at_reference_threshold_needs_review")

    income_sources = set(_as_values(_get_dotted(payload, "financial.income_source_types")))
    if "employment_or_work_income" in income_sources:
        failed.append("employment_or_work_income_not_accepted")
    if not income_sources.intersection(VALID_INCOME_SOURCE_TYPES):
        failed.append("passive_income_source_needs_review")

    available_assets = _as_float(_get_dotted(payload, "financial.available_assets_eur"))
    if available_assets is None or available_assets <= 0:
        failed.append("financial_assets_need_review")


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
    if _is_no(health_insurance_status):
        failed.append("health_insurance_unavailable")
    elif not _is_yes(health_insurance_status):
        failed.append("health_insurance_needs_review")

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

    if consulate_jurisdiction == "paris":
        passport_issued_within_10_years = _get_dotted(
            payload,
            "routing.passport_issued_within_10_years",
        )
        if _is_no(passport_issued_within_10_years):
            failed.append("passport_issued_too_old_for_paris")
        elif not _is_yes(passport_issued_within_10_years):
            failed.append("passport_issue_date_needs_review")


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    _evaluate_applicant_route(payload, failed, routing)
    _evaluate_route_intent(payload, failed)
    _evaluate_financials(payload, failed)
    _evaluate_lodging_insurance_and_passport(payload, failed)

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
    }
