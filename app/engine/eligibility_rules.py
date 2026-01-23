"""
Eligibility Rules (Minimal Stub)

Determines final eligibility status after intake is complete.
This layer does NOT ask questions and does NOT render output.

Rules here should remain deterministic and conservative.
"""

from typing import Dict, List

from app.engine.evidence_validation import validate_income_evidence


INCOME_MIN_MONTHLY_USD = 3000
INCOME_MIN_MONTHS = 12
PASSPORT_MIN_MONTHS = 6

# Evidence requirements (used to emit specific missing-evidence fail keys)
EMPLOYEE_REQUIRED_EVIDENCE = [
    "bank_statements",
    "pay_stubs",
    "employment_contract",
    "tax_returns",
]


def evaluate_eligibility(payload: Dict) -> Dict:
    """
    Evaluate eligibility based on completed intake payload.

    Returns:
    - eligibility_status: eligible | needs_review | not_eligible
    - failed_requirements: list of requirement keys
    """

    failed: List[str] = []

    routing = payload.get("routing", {})
    role = payload.get("role", {})

    work_type = routing.get("work_relationship")

    # --- Income amount (hard minimum) ---
    monthly_income = None

    if work_type == "contractor":
        monthly_income = role.get("contractor", {}).get("monthly_income_usd")
    elif work_type == "employee":
        monthly_income = role.get("employee", {}).get("monthly_income_usd")
    elif work_type == "business_owner":
        monthly_income = role.get("business_owner", {}).get("monthly_income_usd")

    try:
        monthly_income = float(monthly_income)
    except (TypeError, ValueError):
        monthly_income = None

    if monthly_income is None or monthly_income < INCOME_MIN_MONTHLY_USD:
        failed.append("income_amount")

    # --- Income duration (hard minimum) ---
    income_months = None

    if work_type == "contractor":
        income_months = role.get("contractor", {}).get("income_evidence_months")
    elif work_type == "employee":
        income_months = role.get("employee", {}).get("income_evidence_months")
    elif work_type == "business_owner":
        income_months = role.get("business_owner", {}).get("income_evidence_months")

    try:
        # UI sends choice values as strings (e.g., "3", "6", "9", "12")
        income_months = int(income_months)
    except Exception:
        income_months = None

    # Dedicated key so output_builder/taxonomy can map to a single clarification block
    if income_months is None or income_months < INCOME_MIN_MONTHS:
        failed.append("income_duration_months")

    # --- Income evidence type (validation required) ---
    income_evidence = None

    if work_type == "contractor":
        income_evidence = role.get("contractor", {}).get("income_evidence_types")
    elif work_type == "employee":
        income_evidence = role.get("employee", {}).get("income_evidence_types")
    elif work_type == "business_owner":
        income_evidence = role.get("business_owner", {}).get("income_evidence_types")

    is_valid, missing_types = validate_income_evidence(work_type, income_evidence)

    # Ensure we emit ALL missing evidence keys for employee so every failed evidence requirement
    # can be mapped to a clarification block.
    if work_type == "employee" and isinstance(income_evidence, list):
        selected = {x for x in income_evidence if isinstance(x, str) and x}
        missing = [k for k in EMPLOYEE_REQUIRED_EVIDENCE if k not in selected]
        if missing:
            failed.extend(missing)
            is_valid = False

    if not is_valid:
        # Support either return shape from evidence_validation:
        # - (False, ["bank_statements", ...])
        # - (False, "income_evidence") or other string reason key
        if isinstance(missing_types, list):
            failed.extend([m for m in missing_types if isinstance(m, str) and m])
        elif isinstance(missing_types, str) and missing_types:
            failed.append(missing_types)

    # --- Foreign income requirement ---
    if routing.get("income_foreign_only") != "yes":
        failed.append("foreign_income")

    # --- Passport validity ---
    passport_months = routing.get("passport_validity_months")
    try:
        passport_months = int(passport_months)
    except Exception:
        passport_months = None

    if not passport_months or passport_months < PASSPORT_MIN_MONTHS:
        failed.append("passport_validity")

    # --- Background check availability (review only)
    # Do NOT block or mask other failures; handled as informational review flag
    if routing.get("background_check_available") != "yes":
        pass

    # --- Criminal convictions (review gate)
    # Do NOT block or mask other failures; handled as informational review flag
    if routing.get("criminal_record_flag") == "yes":
        pass

    # --- Final status resolution ---
    # Hard requirements that result in immediate ineligibility (NOT just review)
    hard_failures = {
        "income_amount",           # Below minimum monthly income
        "income_duration_months",  # Less than 12 months of income history
        "foreign_income",          # Income not earned outside Costa Rica
        "passport_validity",       # Passport expires too soon
    }
    
    # Check if any hard failures exist
    has_hard_failure = any(req in hard_failures for req in failed)
    
    if has_hard_failure:
        # Hard requirement failures = not eligible
        status = "not_eligible"
    elif failed:
        # Soft failures (missing evidence, review items) = needs review
        status = "needs_review"
    else:
        status = "eligible"

    return {
        "eligibility_status": status,
        "failed_requirements": failed,
        "routing": routing,
        "work_type": work_type,
        "visa_type": "Digital Nomad",
    }