"""Costa Rica Pensionado eligibility rules.

Status-only logic for the Costa Rica Pensionado pathway.
No CTA, redirect, client customization, or output rendering is handled here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


MINIMUM_MONTHLY_PENSION_USD = 1000

VALID_PENSION_SOURCE_TYPES = {
    "social_security",
    "government_pension",
    "private_pension",
    "retirement_benefit",
}

HARD_FAILURES = {
    "not_retired_from_habitual_occupation",
    "pension_income_below_minimum",
    "pension_not_retirement_based",
}


def _get_dotted(payload: Dict[str, Any], dotted_key: str) -> Any:
    cur: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_yes(value: Any) -> bool:
    return value == "yes" or value is True


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    applicant_type = _get_dotted(payload, "routing.applicant_type")
    failed: List[str] = []

    if not _is_yes(_get_dotted(payload, "role.pensionado.retired_from_habitual_occupation")):
        failed.append("not_retired_from_habitual_occupation")

    monthly_pension = _as_float(_get_dotted(payload, "role.pensionado.monthly_pension_usd"))
    if monthly_pension is None or monthly_pension < MINIMUM_MONTHLY_PENSION_USD:
        failed.append("pension_income_below_minimum")

    pension_source_type = _get_dotted(payload, "role.pensionado.pension_source_type")
    if pension_source_type not in VALID_PENSION_SOURCE_TYPES:
        failed.append("pension_source_needs_review")

    if not _is_yes(_get_dotted(payload, "role.pensionado.pension_retirement_based")):
        failed.append("pension_not_retirement_based")

    if not _is_yes(_get_dotted(payload, "role.pensionado.pension_foreign_source_confirmed")):
        failed.append("foreign_pension_source_unconfirmed")

    pension_duration = _get_dotted(payload, "role.pensionado.pension_duration_type")
    if pension_duration != "lifetime_or_indefinite":
        failed.append("pension_duration_needs_review")

    if not _is_yes(_get_dotted(payload, "role.pensionado.pension_certificate_available")):
        failed.append("pension_certificate_unavailable")

    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if passport_months is None or passport_months <= 0:
        failed.append("passport_not_valid")

    if not _is_yes(_get_dotted(payload, "documents.passport_copy_available")):
        failed.append("passport_copy_unavailable")

    if not _is_yes(_get_dotted(payload, "documents.police_clearance_available")):
        failed.append("police_clearance_unavailable")

    if _is_yes(_get_dotted(payload, "routing.criminal_record_flag")):
        failed.append("criminal_record_needs_review")

    if not _is_yes(_get_dotted(payload, "documents.birth_certificate_available")):
        failed.append("birth_certificate_unavailable")

    if not _is_yes(_get_dotted(payload, "documents.passport_photos_available")):
        failed.append("passport_photos_unavailable")

    if not _is_yes(_get_dotted(payload, "documents.filiacion_form_ready")):
        failed.append("filiacion_form_incomplete")

    if not _is_yes(_get_dotted(payload, "documents.request_letter_ready")):
        failed.append("request_letter_incomplete")

    if not _is_yes(_get_dotted(payload, "documents.government_fees_ready")):
        failed.append("government_fees_not_ready")

    if not _is_yes(_get_dotted(payload, "documents.apostille_translation_ready")):
        failed.append("apostille_translation_not_ready")

    if applicant_type == "family":
        dependents_count = _as_int(_get_dotted(payload, "routing.dependents_count"))
        if dependents_count is None or dependents_count < 1:
            failed.append("dependents_count_missing")
        if not _is_yes(_get_dotted(payload, "documents.dependent_documents_available")):
            failed.append("dependent_documents_unavailable")

    ccss_renewal_ready = _get_dotted(payload, "documents.ccss_renewal_ready")
    if ccss_renewal_ready not in {"already_registered", "will_register_after_approval"}:
        failed.append("ccss_renewal_not_ready")

    pension_receipt_evidence = _get_dotted(
        payload,
        "documents.pension_receipt_costa_rica_evidence_available",
    )
    if pension_receipt_evidence not in {"can_document", "will_document_after_approval"}:
        failed.append("pension_receipt_costa_rica_evidence_unavailable")

    if not _is_yes(_get_dotted(payload, "routing.no_work_authorization_acknowledged")):
        failed.append("work_authorization_acknowledgement_missing")

    if not _is_yes(_get_dotted(payload, "routing.temporary_residence_acknowledged")):
        failed.append("temporary_residence_acknowledgement_missing")

    if not _is_yes(_get_dotted(payload, "routing.renewal_every_two_years_acknowledged")):
        failed.append("renewal_acknowledgement_missing")

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
        "pathway": "costa_rica_pensionado",
        "work_type": "pensionado",
        "visa_type": "Costa Rica Pensionado Residency",
    }
