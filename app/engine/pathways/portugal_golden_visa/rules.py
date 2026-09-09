"""Portugal Golden Visa / ARI eligibility rules.

Status-only logic for Portugal's ARI / investment-residence pathway.
This is not D7 passive-income logic and not digital-nomad / remote-work logic.
"""

from __future__ import annotations

from typing import Any, Dict, List


MINIMUM_JOB_CREATION_COUNT = 10
MINIMUM_RESEARCH_INVESTMENT_EUR = 500000
MINIMUM_ARTS_CULTURAL_HERITAGE_INVESTMENT_EUR = 250000
MINIMUM_FUND_INVESTMENT_EUR = 500000
MINIMUM_COMPANY_CAPITALIZATION_INVESTMENT_EUR = 500000

VALID_INVESTMENT_ROUTES = {
    "job_creation",
    "scientific_research",
    "arts_cultural_heritage",
    "non_real_estate_investment_fund",
    "company_capitalization_jobs",
}

VALID_COMPANY_CAPITALIZATION_JOB_PLANS = {
    "create_5_permanent_jobs",
    "maintain_10_jobs_minimum_5_permanent_for_3_years",
}

VALID_TAX_CLEARANCE_STATUSES = {
    "no_outstanding_tax_debts",
    "not_registered_with_the_portuguese_tax_authority",
}

VALID_SOCIAL_SECURITY_CLEARANCE_STATUSES = {
    "no_outstanding_social_security_debts",
    "not_registered_with_portuguese_social_security",
}

# NOTE: Phase B (final canonical-parity cleanup) removed the following
# document-readiness / application-process live questions and all
# eligibility consequences tied solely to them, per the approved
# questions_golden_visa.md:
#   investment.real_estate_only_basis (redundant cross-check of the same
#     real_estate_only_basis fact already captured by investment.route)
#   investment.job_creation.evidence_available
#   investment.fund.subscription_documents_available
#   investment.company_capitalization.company_and_employment_documents_available
#   investment.proof_of_funds_or_transfer_available
#   documents.criminal_record_certificate_available
#   documents.foreign_tax_id_disclosure_available
#   compliance.investment_maintenance_declaration_available
# The scientific-research and arts/cultural-heritage "confirmation available"
# document-readiness questions were replaced (not merely removed) by factual
# qualifying-institution / qualifying-entity questions:
#   investment.scientific_research.institution_confirmation_available
#     -> investment.scientific_research.institution_qualifies
#   investment.arts_cultural_heritage.qualifying_entity_confirmation_available
#     -> investment.arts_cultural_heritage.entity_qualifies
# documents.valid_passport_available was reworded to a factual question and
# its severity was downgraded from a hard failure to needs_review, since not
# currently holding a passport in hand does not establish that a qualifying
# passport cannot be obtained.
# routing.family_documents_available and routing.additional_information were
# already removed in Phase A and remain removed.
#
# See the MoveWise Review Notes in the Phase B final report for the open
# legal/product questions this removal raises. The inert post-eligibility
# fields (compliance.minimum_stay_acknowledged,
# compliance.renewal_investment_maintenance_acknowledged) are unaffected.
HARD_FAILURES = {
    "arts_cultural_heritage_amount_below_minimum",
    "arts_cultural_heritage_entity_not_qualifying",
    "company_capitalization_amount_below_minimum",
    "company_capitalization_job_requirement_not_met",
    "entry_stay_ban",
    "fund_amount_below_minimum",
    "fund_maturity_below_minimum",
    "fund_not_non_real_estate",
    "fund_portuguese_company_investment_below_minimum",
    "job_creation_below_minimum",
    "portuguese_eu_eea_andorra_swiss_national",
    "portuguese_tax_debts",
    "real_estate_only_basis",
    "scientific_research_amount_below_minimum",
    "scientific_research_institution_not_qualifying",
    "serious_criminal_conviction",
    "sii_ucfe_refusal_alert",
    "social_security_debts",
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


def _is_yes(value: Any) -> bool:
    return value == "yes" or value is True


def _is_no(value: Any) -> bool:
    return value == "no" or value is False


def _evaluate_yes_no_requirement(
    payload: Dict[str, Any],
    failed: List[str],
    dotted_key: str,
    *,
    unavailable_key: str,
    review_key: str,
) -> None:
    value = _get_dotted(payload, dotted_key)
    if _is_no(value):
        failed.append(unavailable_key)
    elif not _is_yes(value):
        failed.append(review_key)


def _evaluate_nationality(payload: Dict[str, Any], failed: List[str]) -> None:
    third_country_status = _get_dotted(
        payload,
        "identity.third_country_national_status",
    )
    if third_country_status == "yes":
        failed.append("portuguese_eu_eea_andorra_swiss_national")
    elif third_country_status != "no":
        failed.append("third_country_national_status_needs_review")


def _evaluate_job_creation_route(payload: Dict[str, Any], failed: List[str]) -> None:
    jobs_created = _as_int(
        _get_dotted(payload, "investment.job_creation.jobs_created_count")
    )
    if jobs_created is None:
        failed.append("job_creation_count_missing_or_unrecognized")
    elif jobs_created < MINIMUM_JOB_CREATION_COUNT:
        failed.append("job_creation_below_minimum")


def _evaluate_scientific_research_route(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    amount = _as_float(_get_dotted(payload, "investment.scientific_research.amount_eur"))
    if amount is None:
        failed.append("scientific_research_amount_missing_or_unrecognized")
    elif amount < MINIMUM_RESEARCH_INVESTMENT_EUR:
        failed.append("scientific_research_amount_below_minimum")

    institution_qualifies = _get_dotted(
        payload,
        "investment.scientific_research.institution_qualifies",
    )
    if _is_no(institution_qualifies):
        failed.append("scientific_research_institution_not_qualifying")
    elif not _is_yes(institution_qualifies):
        failed.append("scientific_research_institution_qualification_needs_review")


def _evaluate_arts_cultural_heritage_route(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    amount = _as_float(
        _get_dotted(payload, "investment.arts_cultural_heritage.amount_eur")
    )
    if amount is None:
        failed.append("arts_cultural_heritage_amount_missing_or_unrecognized")
    elif amount < MINIMUM_ARTS_CULTURAL_HERITAGE_INVESTMENT_EUR:
        failed.append("arts_cultural_heritage_amount_below_minimum")

    entity_qualifies = _get_dotted(
        payload,
        "investment.arts_cultural_heritage.entity_qualifies",
    )
    if _is_no(entity_qualifies):
        failed.append("arts_cultural_heritage_entity_not_qualifying")
    elif not _is_yes(entity_qualifies):
        failed.append("arts_cultural_heritage_entity_qualification_needs_review")


def _evaluate_fund_route(payload: Dict[str, Any], failed: List[str]) -> None:
    amount = _as_float(_get_dotted(payload, "investment.fund.amount_eur"))
    if amount is None:
        failed.append("fund_amount_missing_or_unrecognized")
    elif amount < MINIMUM_FUND_INVESTMENT_EUR:
        failed.append("fund_amount_below_minimum")

    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.fund.non_real_estate_confirmed",
        unavailable_key="fund_not_non_real_estate",
        review_key="fund_non_real_estate_status_needs_review",
    )
    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.fund.maturity_at_least_5_years",
        unavailable_key="fund_maturity_below_minimum",
        review_key="fund_maturity_needs_review",
    )
    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.fund.portuguese_company_investment_at_least_60_percent",
        unavailable_key="fund_portuguese_company_investment_below_minimum",
        review_key="fund_portuguese_company_investment_needs_review",
    )


def _evaluate_company_capitalization_route(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    amount = _as_float(
        _get_dotted(payload, "investment.company_capitalization.amount_eur")
    )
    if amount is None:
        failed.append("company_capitalization_amount_missing_or_unrecognized")
    elif amount < MINIMUM_COMPANY_CAPITALIZATION_INVESTMENT_EUR:
        failed.append("company_capitalization_amount_below_minimum")

    job_plan = _get_dotted(
        payload,
        "investment.company_capitalization.jobs_requirement_plan",
    )
    if job_plan == "does_not_meet_job_requirement":
        failed.append("company_capitalization_job_requirement_not_met")
    elif job_plan not in VALID_COMPANY_CAPITALIZATION_JOB_PLANS:
        failed.append("company_capitalization_job_requirement_needs_review")


def _evaluate_investment_route(
    payload: Dict[str, Any],
    failed: List[str],
    routing: Dict[str, Any],
) -> str | None:
    investment_route = _get_dotted(payload, "investment.route")
    routing["investment_route"] = investment_route

    if investment_route == "real_estate_only":
        failed.append("real_estate_only_basis")
        return investment_route

    if investment_route not in VALID_INVESTMENT_ROUTES:
        failed.append("investment_route_missing_or_unrecognized")
        return None

    if investment_route == "job_creation":
        _evaluate_job_creation_route(payload, failed)
    elif investment_route == "scientific_research":
        _evaluate_scientific_research_route(payload, failed)
    elif investment_route == "arts_cultural_heritage":
        _evaluate_arts_cultural_heritage_route(payload, failed)
    elif investment_route == "non_real_estate_investment_fund":
        _evaluate_fund_route(payload, failed)
    elif investment_route == "company_capitalization_jobs":
        _evaluate_company_capitalization_route(payload, failed)

    return investment_route


def _evaluate_applicant_route(payload: Dict[str, Any], failed: List[str]) -> None:
    applicant_type = _get_dotted(payload, "routing.applicant_type")
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


def _evaluate_documents_and_disqualifiers(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    # A "No" (or missing/unclear) valid-passport answer is a correctable
    # readiness gap, not proof that a qualifying passport cannot be obtained,
    # so it is needs_review only -- never a hard failure.
    passport_available = _get_dotted(payload, "documents.valid_passport_available")
    if not _is_yes(passport_available):
        failed.append("passport_needs_review")

    serious_conviction = _get_dotted(
        payload,
        "routing.serious_criminal_conviction_flag",
    )
    if serious_conviction == "yes":
        failed.append("serious_criminal_conviction")
    elif serious_conviction != "no":
        failed.append("serious_criminal_conviction_needs_review")

    entry_stay_ban = _get_dotted(payload, "routing.entry_stay_ban_flag")
    if entry_stay_ban == "yes":
        failed.append("entry_stay_ban")
    elif entry_stay_ban != "no":
        failed.append("entry_stay_ban_needs_review")

    sii_ucfe_refusal_alert = _get_dotted(
        payload,
        "routing.sii_ucfe_refusal_alert_flag",
    )
    if sii_ucfe_refusal_alert == "yes":
        failed.append("sii_ucfe_refusal_alert")
    elif sii_ucfe_refusal_alert != "no":
        failed.append("sii_ucfe_refusal_alert_needs_review")


def _evaluate_tax_and_social_security(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    tax_clearance = _get_dotted(
        payload,
        "documents.portuguese_tax_clearance_status",
    )
    if tax_clearance == "outstanding_portuguese_tax_debts":
        failed.append("portuguese_tax_debts")
    elif tax_clearance not in VALID_TAX_CLEARANCE_STATUSES:
        failed.append("portuguese_tax_clearance_needs_review")

    social_security_clearance = _get_dotted(
        payload,
        "documents.social_security_clearance_status",
    )
    if social_security_clearance == "outstanding_social_security_debts":
        failed.append("social_security_debts")
    elif social_security_clearance not in VALID_SOCIAL_SECURITY_CLEARANCE_STATUSES:
        failed.append("social_security_clearance_needs_review")


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    _evaluate_nationality(payload, failed)
    investment_route = _evaluate_investment_route(payload, failed, routing)
    _evaluate_applicant_route(payload, failed)
    _evaluate_documents_and_disqualifiers(payload, failed)
    _evaluate_tax_and_social_security(payload, failed)

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
        "pathway": "portugal_golden_visa",
        "work_type": "investment_residence",
        "investment_route": investment_route,
        "visa_type": "Portugal Golden Visa / ARI",
        "minimum_investment_thresholds_eur": {
            "scientific_research": MINIMUM_RESEARCH_INVESTMENT_EUR,
            "arts_cultural_heritage": MINIMUM_ARTS_CULTURAL_HERITAGE_INVESTMENT_EUR,
            "non_real_estate_investment_fund": MINIMUM_FUND_INVESTMENT_EUR,
            "company_capitalization_jobs": (
                MINIMUM_COMPANY_CAPITALIZATION_INVESTMENT_EUR
            ),
        },
        "minimum_job_creation_count": MINIMUM_JOB_CREATION_COUNT,
    }
