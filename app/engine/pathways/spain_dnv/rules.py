"""Spain DNV eligibility rules.

Status-only logic for the Spain DNV pathway.
No CTA, redirect, client customization, or output rendering is handled here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set


MINIMUM_MONTHLY_INCOME_EUR = 2800

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

# NOTE: Spain's Ley 14/2013 (Arts. 74 bis / 74 ter) recognizes only two
# statutory work categories for the Digital Nomad Visa: employment activity
# and self-employed/professional activity. QIQ's "business_owner" is not a
# distinct statutory category, so business_owner applicants are first routed
# by role.business_owner.work_structure into whichever statutory category
# actually describes how they're paid, then evaluated with the SAME
# employee-style or contractor-style checks (and the same requirement codes)
# below — see _evaluate_employee_style_foreign_relationship /
# _evaluate_contractor_style_foreign_relationship.
HARD_FAILURES = {
    "income_below_minimum",
    "employee_employer_located_in_spain",
    "employee_foreign_employment_duration_below_minimum",
    "employee_remote_work_not_approved",
    "contractor_foreign_client_relationship_missing",
    "contractor_foreign_client_duration_below_minimum",
    "contractor_spanish_activity_above_threshold",
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
    months, remote-work approval. Used for the employee branch, and reused
    for business_owner applicants who are paid a salary by their business
    (role.business_owner.work_structure == "salary_as_employee")."""
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
    activity. Used for the contractor branch, and reused for business_owner
    applicants who earn business/self-employment income (
    role.business_owner.work_structure == "business_or_self_employment_income")."""
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


def _evaluate_business_owner_foreign_relationship(
    payload: Dict[str, Any], failed: List[str]
) -> None:
    """business_owner has no distinct statutory category under Ley 14/2013 —
    route to whichever real category (employment or self-employed/
    professional activity) the applicant identified via work_structure, and
    apply that category's checks and requirement codes unchanged."""
    work_structure = _get_dotted(payload, "role.business_owner.work_structure")
    if work_structure == "salary_as_employee":
        _evaluate_employee_style_foreign_relationship(
            payload, failed, role_prefix="business_owner"
        )
    elif work_structure == "business_or_self_employment_income":
        _evaluate_contractor_style_foreign_relationship(
            payload, failed, role_prefix="business_owner"
        )
    else:
        failed.append("business_owner_work_structure_needs_review")


def _evaluate_supporting_company_history(
    payload: Dict[str, Any], failed: List[str]
) -> None:
    operating_1_year = _get_dotted(
        payload, "routing.supporting_company_operating_1_year"
    )
    if _is_no(operating_1_year):
        failed.append("supporting_company_operating_history_below_minimum")
    elif not _is_yes(operating_1_year):
        failed.append("supporting_company_operating_history_needs_review")


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
    service_agreements = _get_dotted(
        payload,
        "role.contractor.service_agreements_available",
    )

    failed: List[str] = []

    if work_type not in {"business_owner", "contractor", "employee"}:
        failed.append("work_relationship_missing_or_unrecognized")

    if work_type == "employee":
        _evaluate_employee_style_foreign_relationship(
            payload, failed, role_prefix="employee"
        )

    if (
        work_type == "contractor"
        and service_agreements == "cannot_secure_service_agreements"
    ):
        failed.append("contractor_service_agreements_unavailable")

    if work_type == "contractor":
        _evaluate_contractor_style_foreign_relationship(
            payload, failed, role_prefix="contractor"
        )

    if work_type == "business_owner":
        _evaluate_business_owner_foreign_relationship(payload, failed)

    if work_type in {"employee", "contractor", "business_owner"}:
        _evaluate_supporting_company_history(payload, failed)

    if monthly_income is None:
        failed.append("income_amount_missing_or_unrecognized")
    elif monthly_income < MINIMUM_MONTHLY_INCOME_EUR:
        failed.append("income_below_minimum")

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

    passport_months = _as_int(_get_dotted(payload, "routing.passport_validity_months"))
    if (
        passport_months is None
        or passport_months < MINIMUM_PASSPORT_VALIDITY_MONTHS
    ):
        failed.append("passport_validity_needs_review")

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
