"""Output Builder

Assembles the final user-facing eligibility output using:
- Engine result object (already evaluated)
- Output taxonomies (meta, summary, CTA)
- Clarification taxonomies (work-type specific + shared)

This module contains NO question flow logic.
"""

from typing import Dict, List

from app.engine.taxonomy_loader import load_all_taxonomies

# Load taxonomies once
# NOTE: requires server restart to reflect taxonomy changes.
TAXONOMIES = load_all_taxonomies()


def build_output(result: Dict) -> Dict:
    """Build final eligibility output.

    Expected result keys:
    - eligibility_status
    - work_type
    - visa_type
    - failed_requirements (list)

    Optional (for ALWAYS-show criminal clarification):
    - routing (dict) with keys:
        - background_check_available
        - criminal_record_flag
    """

    status = result.get("eligibility_status")
    work_type = result.get("work_type")
    visa_type = result.get("visa_type")
    failed_requirements: List[str] = result.get("failed_requirements", [])

    output: Dict = {}

    # 1. Meta / Header
    output["meta"] = {
        "status": status,
        "work_type": work_type,
        "visa_type": visa_type,
    }

    # 2. Summary Statement
    summary_tax = TAXONOMIES["output"]["summary_statement"]
    output["summary"] = summary_tax.get("variants", {}).get(status, {}).get("text", "")

    # 3. Clarifications
    clarifications: List[Dict] = []

    # --- ALWAYS-SHOW: Criminal Background clarification (once criminal fields are answered) ---
    # This is informational and should appear whether user selected yes or no.
    routing = result.get("routing") or {}
    bg_answer = routing.get("background_check_available")
    record_answer = routing.get("criminal_record_flag")

    criminal_tax = TAXONOMIES.get("clarification", {}).get("all_work_types")
    # ALWAYS-SHOW trigger: once either criminal question has been answered (value may be "yes"/"no", True/False, etc.)
    if criminal_tax and (
        "background_check_available" in routing
        or "criminal_record_flag" in routing
    ):
        # Accept either taxonomy shape:
        # A) {"scope": "all_work_types", "clarifications": [ {..}, {..} ] }
        # B) a single clarification block dict
        if isinstance(criminal_tax, dict):
            blocks = criminal_tax.get("clarifications")
            if isinstance(blocks, list):
                clarifications.extend([b for b in blocks if isinstance(b, dict)])
            else:
                # Treat as a single block; strip taxonomy-only keys
                clean_block = {k: v for k, v in criminal_tax.items() if k not in {"scope"}}
                clarifications.append(clean_block)

    # --- CONDITIONAL: include clarifications tied to failed requirements ---
    # Show clarifications for both "needs_review" and "not_eligible"
    # For "not_eligible", only strip alternatives for HARD failures
    hard_failures = {
        "income_amount",
        "income_duration_months",
        "foreign_income",
        "passport_validity",
    }
    
    if status in ("needs_review", "not_eligible"):
        # Work-type specific clarifications
        work_tax = TAXONOMIES.get("clarification", {}).get(work_type)
        if work_tax:
            for entry in work_tax.get("clarifications", []):
                requirement = entry.get("requirement")
                if requirement in failed_requirements:
                    # Deep copy the entry to avoid modifying the taxonomy
                    clarification = dict(entry)
                    
                    # For not_eligible status, only remove alternatives for HARD failures
                    if status == "not_eligible" and requirement in hard_failures:
                        # Remove any keys that suggest alternatives
                        clarification.pop("alternative_evidence", None)
                        clarification.pop("secondary_evidence", None)
                        clarification.pop("alternative_evidence_options", None)
                        
                        # Update clarification text for income duration specifically
                        if requirement == "income_duration_months":
                            clarification["clarification"] = (
                                "Costa Rica's Digital Nomad visa requires proof of stable business income "
                                "for at least 12 consecutive months. This is a mandatory requirement with no exceptions."
                            )
                    
                    clarifications.append(clarification)

    # Always include clarifications key (even if empty)
    output["clarifications"] = clarifications

    # 4. Next Steps / CTA
    cta_tax = TAXONOMIES["output"]["next_steps_cta"]
    cta_variant = cta_tax.get("variants", {}).get(status)

    if cta_variant and cta_variant.get("enabled"):
        output["next_steps"] = cta_variant
    elif status == "not_eligible":
        # Fallback for not_eligible if taxonomy doesn't have it
        output["next_steps"] = {
            "enabled": True,
            "text": [
                "Unfortunately, you do not currently meet the mandatory requirements for Costa Rica's Digital Nomad visa.",
                "If your situation changes in the future, you may reapply once all requirements are satisfied."
            ]
        }

    return output