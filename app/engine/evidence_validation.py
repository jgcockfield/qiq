"""
Evidence Validation Rules

Determines whether selected income evidence types are sufficient
based on work relationship.

This module is PURE validation logic:
- No I/O
- No rendering
- No side effects

Returns deterministic pass/fail signals for eligibility_rules.py
"""

from typing import List, Tuple, Dict, Set


# Minimum required evidence types by work type
REQUIRED_EVIDENCE: Dict[str, Set[str]] = {
    "contractor": {"bank_statements", "invoices", "contracts", "tax_returns"},
    "employee": {"pay_stubs", "bank_statements"},
    "business_owner": {"bank_statements", "tax_returns", "profit_loss_statements"},
}


def validate_income_evidence(
    work_type: str,
    evidence_types: List[str] | str | None,
) -> Tuple[bool, List[str]]:
    """
    Validate whether provided evidence types meet minimum requirements.

    Returns:
    - (True, []) if sufficient
    - (False, [missing_types]) if insufficient
    """

    if not evidence_types:
        required = REQUIRED_EVIDENCE.get(work_type, set())
        return False, list(required)

    # Normalize to set
    if isinstance(evidence_types, str):
        # handle comma-separated values from UI
        evidence_set = {e.strip() for e in evidence_types.split(',') if e.strip()}
    else:
        evidence_set = set(evidence_types)

    required = REQUIRED_EVIDENCE.get(work_type, set())

    if not required:
        # Unknown work type → conservative fail
        return False, ["income_evidence"]

    missing = required - evidence_set

    if missing:
        return False, list(missing)

    return True, []