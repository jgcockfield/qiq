"""Spain Student Visa eligibility rules.

Status-only logic for the Spain Student Visa pathway.
No CTA, redirect, client customization, or output rendering is handled here.
"""

from __future__ import annotations

from typing import Any, Dict, List


IPREM_MONTHLY_EUR = 600
MAIN_APPLICANT_IPREM_MULTIPLIER = 1
FIRST_DEPENDENT_IPREM_MULTIPLIER = 0.75
ADDITIONAL_DEPENDENT_IPREM_MULTIPLIER = 0.5
MINIMUM_PASSPORT_VALIDITY_MONTHS = 12
MINIMUM_STUDY_STAY_MONTHS = 3

VALID_STUDY_CATEGORIES = {
    "higher_studies",
    "post_compulsory_secondary",
    "student_mobility",
    "specialized_health_training",
    "volunteering",
    "training",
}

DEPENDENT_ELIGIBLE_STUDY_CATEGORIES = {
    "higher_studies",
    "specialized_health_training",
}

VALID_FUNDS_EVIDENCE_TYPES = {
    "bank_statements",
    "scholarship",
    "family_support",
    "grant",
}

MINIMUM_APPLICATION_TIMING_DAYS = 60

# NOTE: MoveWise review item -- "criminal age in the relevant jurisdiction" has
# no defined numeric threshold anywhere in this pathway's rules or
# requirements_reference.md (age of criminal responsibility is inherently
# jurisdiction-dependent, not a single Spain-wide number). The approved
# canonical flow collects identity.age as a fact, but this screening does not
# yet use it to gate the background-check questions -- see the
# stay_over_6_months derivation and background-check block below, which gate
# on study duration only. Do not add an age threshold here without legal input.
#
# NOTE: MoveWise review item -- study.student_work_intent was simplified from
# a 3-state legal test (no work / compatible part-time work / incompatible or
# over-30-hours work) down to the approved Yes/No question. A bare "yes" can
# no longer be resolved to the old hard-fail-vs-needs-review distinction
# without guessing which of the two prior categories applies, so "yes" is
# treated as needs_review (soft), not an automatic hard failure. See the
# student_work_intent block below.
HARD_FAILURES = {
    "eu_eea_swiss_or_free_movement_status",
    "eu_family_member_route",
    "in_spain_filing_without_lawful_status",
    "study_admission_unavailable",
    "study_program_not_full_time_or_recognized",
    "study_modality_not_eligible",
    "in_person_requirement_not_met",
    "study_stay_not_over_90_days",
    "application_timing_too_late",
    "enrollment_payment_unavailable",
    "insufficient_financial_means",
    "dependents_not_allowed_for_study_category",
    "dependents_work_not_allowed",
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
    multiplier = MAIN_APPLICANT_IPREM_MULTIPLIER
    if dependents_count >= 1:
        multiplier += FIRST_DEPENDENT_IPREM_MULTIPLIER
        multiplier += (dependents_count - 1) * ADDITIONAL_DEPENDENT_IPREM_MULTIPLIER
    return IPREM_MONTHLY_EUR * multiplier


def _review_or_hard_for_yes_no(
    value: Any,
    *,
    hard_when_yes: str | None = None,
    hard_when_no: str | None = None,
    review_key: str,
) -> List[str]:
    if _is_yes(value):
        return [hard_when_yes] if hard_when_yes else []
    if _is_no(value):
        return [hard_when_no] if hard_when_no else []
    return [review_key]


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    failed: List[str] = []

    applicant_type = _get_dotted(payload, "routing.applicant_type")
    if applicant_type not in {"individual", "family"}:
        failed.append("applicant_type_missing")

    eu_eea_swiss_status = _get_dotted(
        payload, "identity.eu_eea_swiss_or_free_movement_status"
    )
    if _is_yes(eu_eea_swiss_status):
        failed.append("eu_eea_swiss_or_free_movement_status")
    elif not _is_no(eu_eea_swiss_status):
        failed.append("eu_eea_swiss_or_free_movement_status_needs_review")
    else:
        # Only reachable (and only asked in the live flow) once
        # eu_eea_swiss_status is confirmed "no" -- see questions.json's
        # applies_when.
        eu_family_member_route = _get_dotted(payload, "identity.eu_family_member_route")
        if _is_yes(eu_family_member_route):
            failed.append("eu_family_member_route")
        elif not _is_no(eu_family_member_route):
            failed.append("eu_family_member_route_needs_review")

    application_route = _get_dotted(payload, "routing.application_route")
    if application_route == "from_within_spain":
        lawful_status = _get_dotted(payload, "routing.lawful_status_in_spain")
        if _is_no(lawful_status):
            failed.append("in_spain_filing_without_lawful_status")
        elif not _is_yes(lawful_status):
            failed.append("in_spain_filing_lawful_status_needs_review")
    elif application_route != "from_outside_spain":
        failed.append("application_route_needs_review")

    study_category = _get_dotted(payload, "study.category")
    if study_category not in VALID_STUDY_CATEGORIES:
        failed.append("study_category_needs_review")

    if application_route == "from_within_spain" and study_category != "higher_studies":
        failed.append("in_spain_filing_route_needs_review")

    admission = _get_dotted(payload, "study.accepted_by_authorized_institution")
    if _is_no(admission):
        failed.append("study_admission_unavailable")
    elif not _is_yes(admission):
        failed.append("study_admission_needs_review")

    full_time = _get_dotted(payload, "study.full_time_recognized_program")
    if _is_no(full_time):
        failed.append("study_program_not_full_time_or_recognized")
    elif not _is_yes(full_time):
        failed.append("study_program_recognition_needs_review")

    modality = _get_dotted(payload, "study.modality")
    if modality == "online":
        failed.append("study_modality_not_eligible")
    elif modality not in {"in_person", "hybrid"}:
        failed.append("study_modality_needs_review")

    # study.in_person_requirement_met only applies (and is only asked) when
    # modality != "in_person" -- see questions.json's applies_when. An
    # in-person program has no separate in-person requirement to satisfy.
    if modality != "in_person":
        in_person_requirement = _get_dotted(payload, "study.in_person_requirement_met")
        if _is_no(in_person_requirement):
            failed.append("in_person_requirement_not_met")
        elif not _is_yes(in_person_requirement):
            failed.append("in_person_requirement_needs_review")

    program_duration_months = _as_float(
        _get_dotted(payload, "study.program_duration_months")
    )
    if program_duration_months is None:
        failed.append("study_duration_missing_or_unrecognized")
    elif program_duration_months <= MINIMUM_STUDY_STAY_MONTHS:
        failed.append("study_stay_not_over_90_days")

    # Stay-over-6-months is now derived directly from program_duration_months
    # rather than a separate self-reported question -- see questions.json's
    # background-check applies_when, which uses the same derived condition.
    stay_over_6_months = (
        program_duration_months is not None and program_duration_months > 6
    )

    timing_days = _as_float(_get_dotted(payload, "study.application_timing_days"))
    if timing_days is None:
        failed.append("application_timing_needs_review")
    elif timing_days >= MINIMUM_APPLICATION_TIMING_DAYS:
        pass
    else:
        justification_available = _get_dotted(
            payload, "study.application_timing_justification_available"
        )
        if _is_yes(justification_available):
            failed.append("application_timing_needs_review")
        elif _is_no(justification_available):
            failed.append("application_timing_too_late")
        else:
            failed.append("application_timing_needs_review")

    enrollment_status = _get_dotted(payload, "study.enrollment_payment_status")
    if enrollment_status == "not_available":
        failed.append("enrollment_payment_unavailable")
    elif enrollment_status in {"responsible_declaration_available", "not_sure"}:
        failed.append("enrollment_payment_needs_review")
    elif enrollment_status != "paid_or_proven":
        failed.append("enrollment_payment_needs_review")

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

        # Whether dependents are allowed is now derived directly from
        # study.category (the reference-defined rule) rather than a separate
        # applicant self-assessment. Same hard-failure code as before.
        if study_category not in DEPENDENT_ELIGIBLE_STUDY_CATEGORIES:
            failed.append("dependents_not_allowed_for_study_category")

        dependents_work = _get_dotted(payload, "routing.dependents_work_intent")
        if _is_yes(dependents_work):
            failed.append("dependents_work_not_allowed")
        elif not _is_no(dependents_work):
            failed.append("dependents_work_intent_needs_review")

    monthly_funds = _as_float(_get_dotted(payload, "financial.monthly_funds_eur"))
    required_financial_means = _required_monthly_financial_means(dependents_count)
    accommodation_prepaid = _get_dotted(
        payload,
        "financial.accommodation_prepaid_full_stay",
    )
    if monthly_funds is None:
        failed.append("financial_means_missing_or_unrecognized")
    elif monthly_funds < required_financial_means:
        if _is_yes(accommodation_prepaid):
            failed.append("financial_means_below_threshold_accommodation_prepaid_review")
        else:
            failed.append("insufficient_financial_means")

    if accommodation_prepaid == "not_sure" or accommodation_prepaid is None:
        failed.append("accommodation_prepaid_needs_review")

    funds_evidence = set(_as_values(_get_dotted(payload, "financial.funds_evidence_types")))
    if not funds_evidence.intersection(VALID_FUNDS_EVIDENCE_TYPES):
        failed.append("financial_evidence_needs_review")

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

    # identity.age is collected per the approved canonical flow but is not
    # yet used here -- see the MoveWise review note above HARD_FAILURES.
    # Background-check questions are gated on study duration alone.
    if stay_over_6_months:
        background_check_available = _get_dotted(
            payload,
            "routing.background_check_available",
        )
        if background_check_available != "yes":
            failed.append("background_check_needs_review")

        criminal_record = _get_dotted(payload, "routing.criminal_record_flag")
        if criminal_record != "no":
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

    # Simplified from a 3-state legal test to the approved Yes/No question --
    # see the MoveWise review note above HARD_FAILURES. "Yes" is routed to
    # manual review rather than an invented hard-fail/pass split.
    student_work_intent = _get_dotted(payload, "study.student_work_intent")
    if _is_yes(student_work_intent):
        failed.append("student_work_intent_needs_review")
    elif not _is_no(student_work_intent):
        failed.append("student_work_intent_needs_review")

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
        "pathway": "spain_student_visa",
        "work_type": "student",
        "visa_type": "Spain Student Visa",
        "required_monthly_financial_means_eur": required_financial_means,
    }
