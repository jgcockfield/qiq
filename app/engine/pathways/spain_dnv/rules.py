"""Spain DNV eligibility rules.

Status-only logic for the Spain DNV pathway.
No CTA, redirect, client customization, or output rendering is handled here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set


# 2026 Spain SMI (salario mínimo interprofesional)-linked income threshold,
# used by Employee, Contractor, and Business Owner. The minimum is 200% of
# the monthly SMI, scaled up for dependents (+75% SMI for the first
# dependent, +25% SMI for each additional dependent), per Ley 14/2013 Art.
# 74 bis / RD 126/2026.
SMI_MONTHLY_EUR_2026 = 1221
EMPLOYEE_INCOME_BASE_SMI_MULTIPLIER = 2.00
EMPLOYEE_INCOME_FIRST_DEPENDENT_SMI_MULTIPLIER = 0.75
EMPLOYEE_INCOME_ADDITIONAL_DEPENDENT_SMI_MULTIPLIER = 0.25

VALID_INCOME_HISTORY_BANDS = {
    "3_to_5",
    "6_to_11",
    "12_or_more",
}

MINIMUM_PASSPORT_VALIDITY_MONTHS = 12

# Statutory thresholds from Ley 14/2013, Arts. 74 bis / 74 ter (Spain's Digital
# Nomad Visa) and the UGE official FAQ: the foreign employment/professional
# relationship relied upon must be at least 3 months old, and a self-employed
# applicant's Spain-based professional activity may not exceed 20% of total
# activity.
MINIMUM_FOREIGN_RELATIONSHIP_MONTHS = 3
MAXIMUM_SPANISH_ACTIVITY_PERCENTAGE = 20

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

EVIDENCE_FAILURE_BY_WORK_TYPE = {
    "employee": "employee_income_evidence_incomplete",
    "contractor": "contractor_income_evidence_incomplete",
    "business_owner": "business_owner_income_evidence_incomplete",
}

# NOTE: QIQ treats Business Owner as ONE work type -- the applicant owns a
# business and earns income from it. Business Owner previously routed
# applicants via role.business_owner.work_structure into an Employee-style
# salary sub-branch or a Contractor-style self-employment sub-branch; that
# subrouting has been removed. Business Owner now has its own dedicated
# questions/checks below, structurally parallel to Employee and Contractor
# but with its own field names and requirement codes throughout.
VALID_QUALIFICATION_OR_EXPERIENCE = {
    "qualifying_education",
    "3_or_more_years_of_relevant_professional_experience",
}

HARD_FAILURES = {
    "employee_income_below_minimum",
    "employee_employer_located_in_spain",
    "employee_foreign_employment_duration_below_minimum",
    "employee_remote_work_not_approved",
    "employee_qualification_or_experience_not_met",
    "contractor_income_below_minimum",
    "contractor_foreign_client_relationship_missing",
    "contractor_foreign_client_duration_below_minimum",
    "contractor_remote_work_not_possible",
    "contractor_qualification_or_experience_not_met",
    "contractor_spanish_activity_above_threshold",
    "business_owner_income_below_minimum",
    "business_owner_business_located_in_spain",
    "business_owner_ownership_duration_below_minimum",
    "business_owner_remote_operation_not_possible",
    "business_owner_qualification_or_experience_not_met",
    "business_owner_spanish_activity_above_threshold",
    "supporting_company_operating_history_below_minimum",
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


def _as_float(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_yes(value: Any) -> bool:
    return value == "yes" or value is True


def _is_no(value: Any) -> bool:
    return value == "no" or value is False


def _has_required_income_evidence(work_type: Any, evidence_types: List[str]) -> bool:
    required = REQUIRED_EVIDENCE_BY_WORK_TYPE.get(str(work_type or ""))
    if not required:
        return False
    return required.issubset(set(evidence_types))


def _role_key(work_type: Any, field_name: str) -> str | None:
    if work_type not in {"business_owner", "contractor", "employee"}:
        return None
    return f"role.{work_type}.{field_name}"


def _get_role_value(payload: Dict[str, Any], work_type: Any, field_name: str) -> Any:
    dotted_key = _role_key(work_type, field_name)
    if not dotted_key:
        return None
    return _get_dotted(payload, dotted_key)


def _evaluate_employee_style_foreign_relationship(
    payload: Dict[str, Any], failed: List[str], role_prefix: str
) -> None:
    """Statutory "employment activity" checks: employer outside Spain, >=3
    months, remote-work approval. Employee-only."""
    employer_outside_spain = _get_dotted(
        payload, f"role.{role_prefix}.employer_outside_spain"
    )
    if _is_no(employer_outside_spain):
        failed.append("employee_employer_located_in_spain")
    elif not _is_yes(employer_outside_spain):
        failed.append("employee_employer_location_needs_review")

    foreign_employment_months = _as_int(
        _get_dotted(payload, f"role.{role_prefix}.foreign_employment_months")
    )
    if foreign_employment_months is None:
        failed.append("employee_foreign_employment_duration_needs_review")
    elif foreign_employment_months < MINIMUM_FOREIGN_RELATIONSHIP_MONTHS:
        failed.append("employee_foreign_employment_duration_below_minimum")

    remote_work_approved = _get_dotted(
        payload, f"role.{role_prefix}.remote_work_approved"
    )
    if _is_no(remote_work_approved):
        failed.append("employee_remote_work_not_approved")
    elif not _is_yes(remote_work_approved):
        failed.append("employee_remote_work_approval_needs_review")


def _evaluate_contractor_style_foreign_relationship(
    payload: Dict[str, Any], failed: List[str], role_prefix: str
) -> None:
    """Statutory "self-employed/professional activity" checks: qualifying
    foreign client/company relationship, >=3 months, <=20% Spain-based
    activity. Contractor-only."""
    foreign_client_relationship = _get_dotted(
        payload, f"role.{role_prefix}.foreign_client_relationship"
    )
    if _is_no(foreign_client_relationship):
        failed.append("contractor_foreign_client_relationship_missing")
    elif not _is_yes(foreign_client_relationship):
        failed.append("contractor_foreign_client_relationship_needs_review")

    foreign_client_months = _as_int(
        _get_dotted(payload, f"role.{role_prefix}.foreign_client_relationship_months")
    )
    if foreign_client_months is None:
        failed.append("contractor_foreign_client_duration_needs_review")
    elif foreign_client_months < MINIMUM_FOREIGN_RELATIONSHIP_MONTHS:
        failed.append("contractor_foreign_client_duration_below_minimum")

    spanish_clients_flag = _get_dotted(
        payload, f"role.{role_prefix}.spanish_clients_flag"
    )
    if _is_yes(spanish_clients_flag):
        spanish_activity_percentage = _as_float(
            _get_dotted(payload, f"role.{role_prefix}.spanish_activity_percentage")
        )
        if spanish_activity_percentage is None:
            failed.append("contractor_spanish_activity_needs_review")
        elif spanish_activity_percentage > MAXIMUM_SPANISH_ACTIVITY_PERCENTAGE:
            failed.append("contractor_spanish_activity_above_threshold")
    elif not _is_no(spanish_clients_flag):
        failed.append("contractor_spanish_activity_needs_review")


def _evaluate_business_owner_location_and_duration(
    payload: Dict[str, Any], failed: List[str]
) -> None:
    """Business Owner-specific facts: the business relied on for this
    application must be based outside Spain, and the applicant must have
    owned/operated it for >=3 months. Deliberately separate from Employee's
    employer-location wording/codes and Contractor's client-relationship
    wording/codes -- Business Owner is its own work type with its own
    dedicated question and codes."""
    business_outside_spain = _get_dotted(
        payload, "role.business_owner.business_outside_spain"
    )
    if _is_no(business_outside_spain):
        failed.append("business_owner_business_located_in_spain")
    elif not _is_yes(business_outside_spain):
        failed.append("business_owner_business_location_needs_review")

    months_owned_operated = _as_int(
        _get_dotted(payload, "role.business_owner.months_owned_operated")
    )
    if months_owned_operated is None:
        failed.append("business_owner_ownership_duration_needs_review")
    elif months_owned_operated < MINIMUM_FOREIGN_RELATIONSHIP_MONTHS:
        failed.append("business_owner_ownership_duration_below_minimum")


def _evaluate_business_owner_remote_operation(
    payload: Dict[str, Any], failed: List[str]
) -> None:
    """Business Owner-specific fact: can the applicant operate their
    business remotely from Spain? Distinct from Employee's
    employer-authorization check and Contractor's remote-work-capability
    question -- uses its own dedicated question/codes."""
    remote_operation_capable = _get_dotted(
        payload, "role.business_owner.remote_operation_capable"
    )
    if _is_no(remote_operation_capable):
        failed.append("business_owner_remote_operation_not_possible")
    elif not _is_yes(remote_operation_capable):
        failed.append("business_owner_remote_operation_needs_review")


def _evaluate_business_owner_spanish_activity(
    payload: Dict[str, Any], failed: List[str]
) -> None:
    """Statutory <=20% Spain-based professional activity cap, evaluated
    against the applicant's own total professional work (not business
    revenue or company-wide client mix). Business Owner-specific, kept
    separate from Contractor's identical-in-substance check so Contractor's
    frozen function is never touched."""
    spanish_clients_flag = _get_dotted(
        payload, "role.business_owner.spanish_clients_flag"
    )
    if _is_yes(spanish_clients_flag):
        spanish_activity_percentage = _as_float(
            _get_dotted(payload, "role.business_owner.spanish_activity_percentage")
        )
        if spanish_activity_percentage is None:
            failed.append("business_owner_spanish_activity_needs_review")
        elif spanish_activity_percentage > MAXIMUM_SPANISH_ACTIVITY_PERCENTAGE:
            failed.append("business_owner_spanish_activity_above_threshold")
    elif not _is_no(spanish_clients_flag):
        failed.append("business_owner_spanish_activity_needs_review")


def _evaluate_supporting_company_history(
    payload: Dict[str, Any],
    failed: List[str],
    dotted_key: str,
) -> None:
    """Shared "company/business operating >=1 year" check. Each of Employee,
    Contractor, and Business Owner has its own dedicated question and passes
    its own dotted_key -- see evaluate_eligibility()."""
    operating_1_year = _get_dotted(payload, dotted_key)
    if _is_no(operating_1_year):
        failed.append("supporting_company_operating_history_below_minimum")
    elif not _is_yes(operating_1_year):
        failed.append("supporting_company_operating_history_needs_review")


def _evaluate_qualification_or_experience(
    payload: Dict[str, Any],
    failed: List[str],
    dotted_key: str,
    *,
    not_met_code: str,
    needs_review_code: str,
) -> None:
    """Verified requirement under Ley 14/2013 Art. 74 bis.2: an applicant
    must hold a qualifying university/vocational-training/business-school
    qualification, or have at least 3 years of relevant professional
    experience. Shared validation logic; each caller supplies its own
    dotted_key and requirement codes so Employee and Contractor get
    correctly-named failures without duplicating the "neither" check.
    Employee's call site/codes are unchanged from before this generalization
    -- see evaluate_eligibility()."""
    value = _get_dotted(payload, dotted_key)
    if value == "neither":
        failed.append(not_met_code)
    elif value not in VALID_QUALIFICATION_OR_EXPERIENCE:
        failed.append(needs_review_code)


def _evaluate_contractor_remote_work_capability(
    payload: Dict[str, Any], failed: List[str]
) -> None:
    """Contractor-specific fact: can the applicant perform their professional
    work remotely from Spain? Distinct from Employee's employer-approval
    check (a contractor has no employer to grant approval), so this uses its
    own dedicated question/codes rather than reusing
    employee_remote_work_not_approved."""
    remote_work_capable = _get_dotted(payload, "role.contractor.remote_work_capable")
    if _is_no(remote_work_capable):
        failed.append("contractor_remote_work_not_possible")
    elif not _is_yes(remote_work_capable):
        failed.append("contractor_remote_work_needs_review")


def _required_smi_scaled_monthly_income_eur(dependents_count: Any) -> float:
    """2026 SMI-linked income threshold: 200% SMI for the applicant, +75% SMI
    for the first dependent, +25% SMI for each additional dependent. Used by
    Employee, Contractor, and Business Owner."""
    count = dependents_count if isinstance(dependents_count, int) else 0
    count = max(count, 0)

    required = EMPLOYEE_INCOME_BASE_SMI_MULTIPLIER * SMI_MONTHLY_EUR_2026
    if count >= 1:
        required += EMPLOYEE_INCOME_FIRST_DEPENDENT_SMI_MULTIPLIER * SMI_MONTHLY_EUR_2026
    if count > 1:
        required += (
            EMPLOYEE_INCOME_ADDITIONAL_DEPENDENT_SMI_MULTIPLIER
            * SMI_MONTHLY_EUR_2026
            * (count - 1)
        )
    return required


def evaluate_eligibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    routing = payload.get("routing", {}) if isinstance(payload, dict) else {}
    work_type = _get_dotted(payload, "routing.work_relationship")
    monthly_income = _as_float(
        _get_role_value(payload, work_type, "monthly_income_eur")
    )
    income_history = _get_role_value(payload, work_type, "income_evidence_months")
    income_evidence = _as_values(
        _get_role_value(payload, work_type, "income_evidence_types")
    )

    failed: List[str] = []

    if work_type not in {"business_owner", "contractor", "employee"}:
        failed.append("work_relationship_missing_or_unrecognized")

    if work_type == "employee":
        _evaluate_employee_style_foreign_relationship(
            payload, failed, role_prefix="employee"
        )

    if work_type == "contractor":
        _evaluate_contractor_style_foreign_relationship(
            payload, failed, role_prefix="contractor"
        )
        _evaluate_contractor_remote_work_capability(payload, failed)

    if work_type == "business_owner":
        _evaluate_business_owner_location_and_duration(payload, failed)
        _evaluate_business_owner_remote_operation(payload, failed)
        _evaluate_business_owner_spanish_activity(payload, failed)

    if work_type == "employee":
        _evaluate_supporting_company_history(
            payload, failed, "role.employee.employer_company_operating_1_year"
        )
        _evaluate_qualification_or_experience(
            payload,
            failed,
            "role.employee.qualification_or_experience",
            not_met_code="employee_qualification_or_experience_not_met",
            needs_review_code="employee_qualification_or_experience_needs_review",
        )
    elif work_type == "contractor":
        _evaluate_supporting_company_history(
            payload, failed, "role.contractor.foreign_company_operating_1_year"
        )
        _evaluate_qualification_or_experience(
            payload,
            failed,
            "role.contractor.qualification_or_experience",
            not_met_code="contractor_qualification_or_experience_not_met",
            needs_review_code="contractor_qualification_or_experience_needs_review",
        )
    elif work_type == "business_owner":
        _evaluate_supporting_company_history(
            payload, failed, "role.business_owner.business_operating_1_year"
        )
        _evaluate_qualification_or_experience(
            payload,
            failed,
            "role.business_owner.qualification_or_experience",
            not_met_code="business_owner_qualification_or_experience_not_met",
            needs_review_code="business_owner_qualification_or_experience_needs_review",
        )

    if monthly_income is None:
        failed.append("income_amount_missing_or_unrecognized")
    elif work_type in {"employee", "contractor", "business_owner"}:
        dependents_count = _as_int(_get_dotted(payload, "routing.dependents_count"))
        required_income = _required_smi_scaled_monthly_income_eur(dependents_count)
        if monthly_income < required_income:
            failed.append(f"{work_type}_income_below_minimum")

    if income_history not in VALID_INCOME_HISTORY_BANDS:
        failed.append("income_duration_needs_review")

    if not _has_required_income_evidence(work_type, income_evidence):
        failed.append(
            EVIDENCE_FAILURE_BY_WORK_TYPE.get(
                str(work_type or ""),
                "income_evidence_incomplete",
            )
        )

    applicant_type = _get_dotted(payload, "routing.applicant_type")
    dependents_count = _get_dotted(payload, "routing.dependents_count")
    if applicant_type == "family" and dependents_count in (None, ""):
        failed.append("dependents_count_missing")
    elif applicant_type not in {"individual", "family"}:
        failed.append("dependents_count_missing")

    # Missing-input validation only for the existing, canonical-approved
    # family fields routing.dependent_relationships / routing.dependent_ages.
    # This checks that the already-required facts were actually supplied --
    # it does NOT classify any relationship as acceptable/unacceptable, does
    # NOT impose an age threshold, and never affects individual applicants or
    # the SMI/dependent-count income formula above.
    if applicant_type == "family":
        if not _as_values(_get_dotted(payload, "routing.dependent_relationships")):
            failed.append("dependent_relationships_missing")
        if not _as_values(_get_dotted(payload, "routing.dependent_ages")):
            failed.append("dependent_ages_missing")

    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if (
        passport_months is None
        or passport_months < MINIMUM_PASSPORT_VALIDITY_MONTHS
    ):
        failed.append("passport_validity_needs_review")

    # MoveWise note: confirm whether health_insurance_status == "will_obtain"
    # should remain a passing state or route to needs_review. Current
    # approved runtime behavior (treated as a pass, identical to "have_it")
    # is intentionally preserved here pending legal/product confirmation --
    # NOT changed merely because sibling pathways (Portugal D7/DNV, Spain
    # NLV, Spain Student Visa) route the same choice value to needs_review.
    health_insurance_status = _get_dotted(payload, "routing.health_insurance_status")
    if health_insurance_status not in {"have_it", "will_obtain"}:
        failed.append("health_insurance_not_ready")

    if not _is_yes(_get_dotted(payload, "documents.police_clearance_available")):
        failed.append("police_clearance_unavailable")

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
        "work_type": work_type,
        "visa_type": "Spain Digital Nomad Visa",
    }
