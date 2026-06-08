"""Spain DNV eligibility rules.

Status-only logic for the Spain DNV pathway.
No CTA, redirect, client customization, or output rendering is handled here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set


ELIGIBLE_INCOME_BANDS = {
    "eur_2800_5000",
    "eur_5000_10000",
    "above_10000",
}

VALID_INCOME_HISTORY_BANDS = {
    "3_to_5",
    "6_to_11",
    "12_or_more",
}

MINIMUM_PASSPORT_VALIDITY_MONTHS = 12

REQUIRED_EVIDENCE_BY_WORK_TYPE: Dict[str, Set[str]] = {
    "employee": {"bank_statements", "employment_contract", "pay_stubs"},
    "contractor": {
        "bank_statements",
        "service_agreements_or_contracts",
        "invoices",
    },
    "business_owner": {
        "bank_statements",
        "business_registration",
        "tax_returns_or_financial_statements",
    },
}

HARD_FAILURES = {
    "income_below_minimum",
    "foreign_income_source_unconfirmed",
}


def _get_dotted(payload: Dict[str, Any], dotted_key: str) -> Any:
    cur: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _as_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_yes(value: Any) -> bool:
    return value == "yes" or value is True


def _has_required_income_evidence(work_type: Any, evidence_types: List[str]) -> bool:
    required = REQUIRED_EVIDENCE_BY_WORK_TYPE.get(str(work_type or ""))
    if not required:
        return False
    return required.issubset(set(evidence_types))


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    service_interest = _as_values(_get_dotted(payload, "routing.service_interest"))
    work_type = _get_dotted(payload, "routing.work_relationship")
    income_band = _get_dotted(payload, "income.gross_monthly_income_band_eur")
    income_history = _get_dotted(payload, "income.income_history_months")
    income_evidence = _as_values(_get_dotted(payload, "income.income_evidence_types"))
    service_agreements = _get_dotted(
        payload,
        "role.contractor.service_agreements_available",
    )

    failed: List[str] = []

    if "digital_nomad_visa" not in service_interest:
        return {
            "eligibility_status": "needs_review",
            "failed_requirements": ["non_dnv_service_interest"],
            "routing": routing,
            "work_type": work_type,
            "visa_type": "Spain Digital Nomad Visa",
        }

    if work_type not in {"business_owner", "contractor", "employee"}:
        failed.append("work_relationship_missing_or_unrecognized")

    if (
        work_type == "contractor"
        and service_agreements == "cannot_secure_service_agreements"
    ):
        failed.append("contractor_service_agreements_unavailable")

    if not _is_yes(_get_dotted(payload, "routing.income_foreign_only")):
        failed.append("foreign_income_source_unconfirmed")

    if income_band == "below_2800":
        failed.append("income_below_minimum")
    elif income_band not in ELIGIBLE_INCOME_BANDS:
        failed.append("income_band_missing_or_unrecognized")

    if income_history not in VALID_INCOME_HISTORY_BANDS:
        failed.append("income_duration_needs_review")

    if not _has_required_income_evidence(work_type, income_evidence):
        failed.append("income_evidence_incomplete")

    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if (
        passport_months is None
        or passport_months < MINIMUM_PASSPORT_VALIDITY_MONTHS
    ):
        failed.append("passport_validity_needs_review")

    if not _is_yes(_get_dotted(payload, "documents.police_clearance_available")):
        failed.append("police_clearance_unavailable")

    if _is_yes(_get_dotted(payload, "routing.criminal_record_flag")):
        failed.append("criminal_record_needs_review")

    health_insurance_status = _get_dotted(payload, "routing.health_insurance_status")
    if health_insurance_status not in {"have_it", "will_obtain"}:
        failed.append("health_insurance_not_ready")

    has_dependents = _get_dotted(payload, "routing.has_dependents")
    dependents_count = _get_dotted(payload, "routing.dependents_count")
    if has_dependents == "yes":
        if dependents_count in (None, ""):
            failed.append("dependents_count_missing")
        if not _is_yes(_get_dotted(payload, "documents.dependent_documents_available")):
            failed.append("dependent_documents_unavailable")
    elif has_dependents != "no":
        failed.append("dependents_count_missing")

    if not _is_yes(_get_dotted(payload, "documents.civil_documents_available")):
        failed.append("civil_documents_unavailable")

    if not _is_yes(_get_dotted(payload, "documents.apostille_translation_ready")):
        failed.append("apostille_translation_not_ready")

    if not _is_yes(_get_dotted(payload, "routing.renewal_compliance_acknowledged")):
        failed.append("renewal_compliance_acknowledgement_missing")

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
        "work_type": work_type,
        "visa_type": "Spain Digital Nomad Visa",
    }
