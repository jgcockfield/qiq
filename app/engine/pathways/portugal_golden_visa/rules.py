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

VALID_FOREIGN_TAX_ID_STATUSES = {
    "yes",
    "proof_none_exists",
}

# NOTE: routing.family_documents_available and routing.additional_information
# were removed from the live eligibility flow (and from this module) per Phase
# A of the approved Portugal Golden Visa cleanup (questions_golden_visa.md).
# family_documents_available's only eligibility consequence
# (family_documents_needs_review) was never a hard failure, so removing it
# loses no substantive eligibility behavior. additional_information had no
# eligibility effect at all (required: false, never evaluated).
#
# The following fields remain live with UNCHANGED behavior pending MoveWise
# legal/product review, per Phase A scope: investment.real_estate_only_basis,
# investment.job_creation.evidence_available,
# investment.scientific_research.institution_confirmation_available,
# investment.arts_cultural_heritage.qualifying_entity_confirmation_available,
# investment.fund.subscription_documents_available,
# investment.company_capitalization.company_and_employment_documents_available,
# investment.proof_of_funds_or_transfer_available,
# documents.valid_passport_available,
# documents.criminal_record_certificate_available,
# documents.foreign_tax_id_disclosure_available,
# compliance.investment_maintenance_declaration_available.
HARD_FAILURES = {
    "arts_cultural_heritage_amount_below_minimum",
    "arts_cultural_heritage_qualifying_entity_unavailable",
    "company_capitalization_amount_below_minimum",
    "company_capitalization_documents_unavailable",
    "company_capitalization_job_requirement_not_met",
    "entry_stay_ban",
    "foreign_tax_id_disclosure_unavailable",
    "fund_amount_below_minimum",
    "fund_maturity_below_minimum",
    "fund_not_non_real_estate",
    "fund_portuguese_company_investment_below_minimum",
    "fund_subscription_documents_unavailable",
    "investment_maintenance_declaration_unavailable",
    "investment_proof_or_transfer_unavailable",
    "job_creation_below_minimum",
    "job_creation_evidence_unavailable",
    "passport_unavailable",
    "portuguese_eu_eea_andorra_swiss_national",
    "portuguese_tax_debts",
    "real_estate_only_basis",
    "scientific_research_amount_below_minimum",
    "scientific_research_institution_confirmation_unavailable",
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

    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.job_creation.evidence_available",
        unavailable_key="job_creation_evidence_unavailable",
        review_key="job_creation_evidence_needs_review",
    )


def _evaluate_scientific_research_route(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    amount = _as_float(_get_dotted(payload, "investment.scientific_research.amount_eur"))
    if amount is None:
        failed.append("scientific_research_amount_missing_or_unrecognized")
    elif amount < MINIMUM_RESEARCH_INVESTMENT_EUR:
        failed.append("scientific_research_amount_below_minimum")

    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.scientific_research.institution_confirmation_available",
        unavailable_key="scientific_research_institution_confirmation_unavailable",
        review_key="scientific_research_institution_confirmation_needs_review",
    )


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

    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.arts_cultural_heritage.qualifying_entity_confirmation_available",
        unavailable_key="arts_cultural_heritage_qualifying_entity_unavailable",
        review_key="arts_cultural_heritage_qualifying_entity_needs_review",
    )


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
    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.fund.subscription_documents_available",
        unavailable_key="fund_subscription_documents_unavailable",
        review_key="fund_subscription_documents_needs_review",
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

    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.company_capitalization.company_and_employment_documents_available",
        unavailable_key="company_capitalization_documents_unavailable",
        review_key="company_capitalization_documents_needs_review",
    )


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

    real_estate_only = _get_dotted(payload, "investment.real_estate_only_basis")
    if _is_yes(real_estate_only):
        failed.append("real_estate_only_basis")
    elif not _is_no(real_estate_only):
        failed.append("real_estate_only_basis_needs_review")

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

    _evaluate_yes_no_requirement(
        payload,
        failed,
        "investment.proof_of_funds_or_transfer_available",
        unavailable_key="investment_proof_or_transfer_unavailable",
        review_key="investment_proof_or_transfer_needs_review",
    )

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

    # NOTE: routing.family_documents_available was removed from the live
    # eligibility flow (and from this function) per Phase A of the approved
    # Portugal Golden Visa cleanup -- its only consequence
    # (family_documents_needs_review) was never a hard failure.
    #
    # NOTE: process.portal_ari_family_application_acknowledged was removed
    # from the live eligibility flow (and from this function) because it
    # describes a portal/process step, not a fact needed to determine INITIAL
    # eligibility. See questions.json's "post_eligibility_checklist" block and
    # clarifications.json for the preserved question/requirement content.


def _evaluate_documents_and_disqualifiers(
    payload: Dict[str, Any],
    failed: List[str],
) -> None:
    _evaluate_yes_no_requirement(
        payload,
        failed,
        "documents.valid_passport_available",
        unavailable_key="passport_unavailable",
        review_key="passport_needs_review",
    )

    criminal_certificate = _get_dotted(
        payload,
        "documents.criminal_record_certificate_available",
    )
    if criminal_certificate == "no":
        failed.append("criminal_record_certificate_unavailable")
    elif criminal_certificate == "available_but_needs_translation_or_apostille":
        failed.append("criminal_record_certificate_needs_translation_or_apostille")
    elif criminal_certificate != "yes_recent_translated_apostilled":
        failed.append("criminal_record_certificate_needs_review")

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


def _evaluate_tax_social_security_and_ids(
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

    foreign_tax_id = _get_dotted(
        payload,
        "documents.foreign_tax_id_disclosure_available",
    )
    if _is_no(foreign_tax_id):
        failed.append("foreign_tax_id_disclosure_unavailable")
    elif foreign_tax_id not in VALID_FOREIGN_TAX_ID_STATUSES:
        failed.append("foreign_tax_id_disclosure_needs_review")


def _evaluate_compliance(payload: Dict[str, Any], failed: List[str]) -> None:
    _evaluate_yes_no_requirement(
        payload,
        failed,
        "compliance.investment_maintenance_declaration_available",
        unavailable_key="investment_maintenance_declaration_unavailable",
        review_key="investment_maintenance_declaration_needs_review",
    )

    # NOTE: compliance.minimum_stay_acknowledged and
    # compliance.renewal_investment_maintenance_acknowledged were removed from
    # the live eligibility flow (and from this function) because they describe
    # post-approval / renewal-stage steps, not facts needed to determine INITIAL
    # eligibility. They are preserved in questions.json's
    # "post_eligibility_checklist" block and in clarifications.json.
    #
    # NOTE: process.portal_ari_acknowledged and
    # compliance.permanent_residence_later_stage_acknowledged were removed
    # entirely (not preserved) -- the former is a pure portal-process
    # disclaimer, and the latter describes a separate, later-stage application
    # (permanent residence) with no ARI-eligibility relevance.


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    _evaluate_nationality(payload, failed)
    investment_route = _evaluate_investment_route(payload, failed, routing)
    _evaluate_applicant_route(payload, failed)
    _evaluate_documents_and_disqualifiers(payload, failed)
    _evaluate_tax_social_security_and_ids(payload, failed)
    _evaluate_compliance(payload, failed)

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
