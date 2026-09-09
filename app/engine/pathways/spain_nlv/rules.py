"""Spain NLV eligibility rules.

Status-only logic for the Spain Non-Lucrative Visa pathway.
No CTA, redirect, client customization, or output rendering is handled here.
"""

from __future__ import annotations

from typing import Any, Dict, List


IPREM_MONTHLY_EUR = 600
MAIN_APPLICANT_IPREM_MULTIPLIER = 4
DEPENDENT_IPREM_MULTIPLIER = 1
MINIMUM_PASSPORT_VALIDITY_MONTHS = 12

VALID_FUNDS_EVIDENCE_TYPES = {
    "bank_certificates",
    "property_titles",
    "certified_checks",
    "credit_cards_with_bank_certification",
    "passive_income_proof",
}

# NOTE: routing.renewal_residence_days_expected was removed from the live
# eligibility flow (and from this function) because the >183-days-per-year
# rule is a RENEWAL-stage requirement per requirements_reference.md, not a
# fact needed to determine INITIAL eligibility. See questions.json's
# "post_eligibility_checklist" block for the preserved question content and
# clarifications.json for the preserved (now dormant) requirement code.
#
# NOTE: a disclosed criminal record is intentionally kept as
# "criminal_record_needs_review" (soft, manual review) rather than an
# automatic hard failure -- Spanish law disqualifies only for "offenses
# recognized under Spanish law," which requires case-by-case legal judgment
# that this screening does not attempt to make.
HARD_FAILURES = {
    "eu_eea_swiss_citizen",
    "eu_family_member_route",
    "work_activity_in_spain",
    "irregular_presence_in_spain",
    "insufficient_financial_means",
    "spanish_company_labor_activity",
    "passport_validity_below_minimum",
    "health_insurance_unavailable",
    "public_order_security_risk",
    "serious_public_health_disease",
}


def _get_dotted(payload: Dict[str, Any], dotted_key: str) -> Any:
    cur: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _as_float(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        return int(value)
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


def _required_monthly_financial_means(dependents_count: int) -> float:
    multiplier = MAIN_APPLICANT_IPREM_MULTIPLIER + (
        dependents_count * DEPENDENT_IPREM_MULTIPLIER
    )
    return IPREM_MONTHLY_EUR * multiplier


def _evaluate_eu_status(payload: Dict[str, Any], failed: List[str]) -> None:
    eu_citizen = _get_dotted(payload, "identity.eu_eea_swiss_citizen")
    if _is_yes(eu_citizen):
        failed.append("eu_eea_swiss_citizen")
        return
    if not _is_no(eu_citizen):
        failed.append("eu_eea_swiss_citizen_needs_review")
        return

    # Only reachable (and only asked in the live flow) once eu_citizen is
    # confirmed "no" -- see questions.json's applies_when.
    family_member_route = _get_dotted(payload, "identity.eu_family_member_route")
    if _is_yes(family_member_route):
        failed.append("eu_family_member_route")
    elif not _is_no(family_member_route):
        failed.append("eu_family_member_route_needs_review")


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    applicant_type = _get_dotted(payload, "routing.applicant_type")
    if applicant_type not in {"individual", "family"}:
        failed.append("applicant_type_missing")

    _evaluate_eu_status(payload, failed)

    intends_to_work = _get_dotted(payload, "work.intends_to_work_in_spain")
    if _is_yes(intends_to_work):
        failed.append("work_activity_in_spain")
    elif not _is_no(intends_to_work):
        failed.append("work_intent_needs_review")

    irregular_presence = _get_dotted(payload, "routing.irregular_presence_spain")
    if _is_yes(irregular_presence):
        failed.append("irregular_presence_in_spain")
    elif not _is_no(irregular_presence):
        failed.append("irregular_presence_needs_review")

    dependents_count = 0
    if applicant_type == "family":
        parsed_dependents_count = _as_int(_get_dotted(payload, "routing.dependents_count"))
        if parsed_dependents_count is None or parsed_dependents_count < 1:
            failed.append("dependents_count_missing")
        else:
            dependents_count = parsed_dependents_count

        if not _get_dotted(payload, "routing.dependent_relationships"):
            failed.append("dependent_relationships_missing")
        if not _get_dotted(payload, "routing.dependent_ages"):
            failed.append("dependent_ages_missing")

        schooling = _get_dotted(
            payload,
            "routing.minor_children_schooling_status",
        )
        if _is_no(schooling):
            failed.append("minor_children_schooling_issue")
        elif schooling not in {"yes", "not_applicable"}:
            failed.append("minor_children_schooling_needs_review")

    monthly_financial_means = _as_float(
        _get_dotted(payload, "financial.monthly_passive_income_or_assets_eur")
    )
    required_financial_means = _required_monthly_financial_means(dependents_count)
    if monthly_financial_means is None:
        failed.append("financial_means_missing_or_unrecognized")
    elif monthly_financial_means < required_financial_means:
        failed.append("insufficient_financial_means")

    funds_evidence = set(_as_values(_get_dotted(payload, "financial.funds_evidence_types")))
    if not funds_evidence.intersection(VALID_FUNDS_EVIDENCE_TYPES):
        failed.append("financial_evidence_needs_review")

    spanish_company_ownership = _get_dotted(
        payload,
        "financial.spanish_company_ownership",
    )
    if _is_yes(spanish_company_ownership):
        performs_labor = _get_dotted(
            payload,
            "financial.performs_labor_for_spanish_company",
        )
        if _is_yes(performs_labor):
            failed.append("spanish_company_labor_activity")
        elif not _is_no(performs_labor):
            failed.append("spanish_company_labor_activity_needs_review")
    elif not _is_no(spanish_company_ownership):
        failed.append("spanish_company_ownership_needs_review")

    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if passport_months is None:
        failed.append("passport_validity_missing_or_unrecognized")
    elif passport_months < MINIMUM_PASSPORT_VALIDITY_MONTHS:
        failed.append("passport_validity_below_minimum")

    health_insurance_status = _get_dotted(payload, "routing.health_insurance_status")
    if _is_no(health_insurance_status):
        failed.append("health_insurance_unavailable")
    elif health_insurance_status != "have_it":
        failed.append("health_insurance_needs_review")

    background_check_available = _get_dotted(
        payload,
        "routing.background_check_available",
    )
    if background_check_available != "yes":
        failed.append("background_check_needs_review")

    criminal_record = _get_dotted(payload, "routing.criminal_record_flag")
    if criminal_record == "yes":
        failed.append("criminal_record_needs_review")
    elif criminal_record != "no":
        failed.append("criminal_record_needs_review")

    public_order_risk = _get_dotted(
        payload,
        "routing.public_order_security_risk_flag",
    )
    if public_order_risk == "yes":
        failed.append("public_order_security_risk")
    elif public_order_risk != "no":
        failed.append("public_order_security_needs_review")

    public_health_disease = _get_dotted(
        payload,
        "routing.public_health_disease_flag",
    )
    if public_health_disease == "yes":
        failed.append("serious_public_health_disease")
    elif public_health_disease != "no":
        failed.append("public_health_needs_review")

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
        "pathway": "spain_nlv",
        "work_type": "non_lucrative",
        "visa_type": "Spain Non-Lucrative Visa",
        "required_monthly_financial_means_eur": required_financial_means,
    }
