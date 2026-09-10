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

# NOTE: the following live questions were removed during the canonical
# cleanup (questions_pensionado.md) because they test document/evidence
# readiness, filing procedure, or dead intake data rather than facts needed
# to determine INITIAL eligibility, and all eligibility consequences tied
# solely to them were removed alongside them:
#   role.pensionado.pension_foreign_source_confirmed (foreign_pension_source_unconfirmed)
#   role.pensionado.pension_certificate_available (pension_certificate_unavailable)
#   documents.dependent_documents_available (dependent_documents_unavailable)
#   documents.passport_copy_available (passport_copy_unavailable)
#   documents.police_clearance_available (police_clearance_unavailable)
#   documents.birth_certificate_available (birth_certificate_unavailable)
#   documents.passport_photos_available (passport_photos_unavailable)
#   documents.filiacion_form_ready (filiacion_form_incomplete)
#   documents.request_letter_ready (request_letter_incomplete)
#   documents.government_fees_ready (government_fees_not_ready)
#   documents.apostille_translation_ready (apostille_translation_not_ready)
#   identity.nationality (never evaluated; no eligibility consequence)
#   identity.country_of_residence (never evaluated; no eligibility consequence)
#   routing.additional_information (required: false; no eligibility consequence)
# documents.pension_receipt_costa_rica_evidence_available was relocated (not
# deleted) into questions.json's post_eligibility_checklist block, along with
# the already-inert documents.ccss_renewal_ready and
# routing.renewal_every_two_years_acknowledged -- none of the three are
# emitted by this module. See clarifications.json/output.json for the
# preserved (stage-tagged) requirement content, and the MoveWise Review Notes
# in the implementation report for the open legal/product questions these
# removals and relocations raise.
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
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
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


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    applicant_type = _get_dotted(payload, "routing.applicant_type")
    failed: List[str] = []

    if applicant_type not in {"individual", "family"}:
        failed.append("applicant_type_missing")

    if not _is_yes(_get_dotted(payload, "role.pensionado.retired_from_habitual_occupation")):
        failed.append("not_retired_from_habitual_occupation")

    monthly_pension = _as_float(_get_dotted(payload, "role.pensionado.monthly_pension_usd"))
    if monthly_pension is None:
        failed.append("pension_income_missing_or_unrecognized")
    elif monthly_pension < MINIMUM_MONTHLY_PENSION_USD:
        failed.append("pension_income_below_minimum")

    pension_source_type = _get_dotted(payload, "role.pensionado.pension_source_type")
    if pension_source_type not in VALID_PENSION_SOURCE_TYPES:
        # Covers "other" and any missing/unrecognized value -- "other" is a
        # non-standard source that always requires manual review, regardless
        # of how the retirement-basis follow-up below is answered.
        failed.append("pension_source_needs_review")

    # The retirement-basis follow-up is only asked (see questions.json's
    # applies_when) when pension_source_type == "other". For the four named
    # source types, the retirement/pension-benefit characterization is
    # already implied by the source selection itself, so the field is never
    # presented and must not be treated as a missing-answer failure.
    if pension_source_type == "other":
        if not _is_yes(_get_dotted(payload, "role.pensionado.pension_retirement_based")):
            failed.append("pension_not_retirement_based")

    pension_has_scheduled_end_date = _get_dotted(
        payload,
        "role.pensionado.pension_has_scheduled_end_date",
    )
    if pension_has_scheduled_end_date != "no":
        # Covers "yes" (a scheduled end date exists) and any missing/unclear
        # value -- only an explicit "no" (lifetime/indefinite) passes.
        failed.append("pension_duration_needs_review")

    if not _is_no(_get_dotted(payload, "work.intends_to_work_in_costa_rica")):
        failed.append("work_authorization_acknowledgement_missing")

    if applicant_type == "family":
        dependents_count = _as_int(_get_dotted(payload, "routing.dependents_count"))
        if dependents_count is None or dependents_count < 1:
            failed.append("dependents_count_missing")

    if not _is_yes(_get_dotted(payload, "documents.valid_passport_available")):
        failed.append("passport_not_valid")

    if _is_yes(_get_dotted(payload, "routing.criminal_record_flag")):
        failed.append("criminal_record_needs_review")

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
