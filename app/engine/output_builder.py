"""Output Builder

Assembles the final user-facing eligibility output using:
- Engine result object (already evaluated)
- Output taxonomies (meta, summary, CTA)
- Clarification taxonomies (work-type specific + shared)

This module contains NO question flow logic.

Presentation layer
-------------------
This module is also the single, centralized place that converts internal
snake_case values (the `eligibility_status` enum and requirement/reason
codes) into applicant-facing display strings. Internal values themselves are
never renamed -- `humanize_status()`/`humanize_requirement_code()` /
`display_title_for_clarification()` only compute an additional, additive
*display* string alongside the existing machine-readable fields:

- `output["meta"]["status_display"]` -- e.g. "Not Eligible" for "not_eligible"
- each `output["clarifications"][i]["display_title"]` -- the existing
  clarification `title` when present, otherwise a mechanically humanized
  fallback of the requirement code (never the raw snake_case code itself)

Every applicant-facing surface (widget, PDF/EDR export) should prefer these
`*_display`/`display_title` fields over the raw machine values, falling back
to their own local humanization only as defense-in-depth.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.engine.pathway_registry import resolve_pathway
from app.engine.taxonomy_loader import load_all_taxonomies

# Load taxonomies once
# NOTE: requires server restart to reflect taxonomy changes.
TAXONOMIES = load_all_taxonomies()
SPAIN_DNV_OUTPUT_PATH = Path(__file__).resolve().parent / "pathways" / "spain_dnv" / "output.json"
SPAIN_DNV_CLARIFICATIONS_PATH = Path(__file__).resolve().parent / "pathways" / "spain_dnv" / "clarifications.json"

# Explicit display strings for the three known internal status values. Any
# other/unrecognized status value falls back to mechanical humanization
# rather than leaking snake_case.
_STATUS_DISPLAY_MAP = {
    "eligible": "Eligible",
    "needs_review": "Needs Review",
    "not_eligible": "Not Eligible",
}


def humanize_requirement_code(code: Any) -> str:
    """Mechanical snake_case -> Title Case fallback humanization.

    This is a FALLBACK ONLY. Whenever an explicit applicant-facing
    clarification title exists, prefer that instead -- see
    `display_title_for_clarification()`.
    """
    if not code:
        return ""
    words = [w for w in str(code).replace("-", "_").split("_") if w]
    return " ".join(w.capitalize() for w in words)


def humanize_status(status: Any) -> str:
    """Applicant-facing display string for an internal eligibility_status
    value (or any other internal snake_case status-like value). Never
    returns the raw snake_case value for a recognized or unrecognized
    status -- unrecognized values fall back to mechanical humanization."""
    if not status:
        return ""
    return _STATUS_DISPLAY_MAP.get(status, humanize_requirement_code(status))


def display_title_for_clarification(clarification: Any) -> str:
    """Resolve the applicant-facing title for one clarification entry.

    Priority:
    1. The clarification's own explicit `title` (applicant-facing, already
       authored in clarifications.json).
    2. A mechanically humanized fallback of the internal `requirement` code.

    The raw snake_case `requirement` code is never returned as-is.
    """
    if not isinstance(clarification, dict):
        return ""
    title = clarification.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return humanize_requirement_code(clarification.get("requirement"))


def _with_display_title(clarification: Any) -> Any:
    """Return a copy of `clarification` with a guaranteed `display_title`
    added, without mutating the original (which may be a taxonomy entry
    loaded once at module import and shared across requests)."""
    if not isinstance(clarification, dict):
        return clarification
    augmented = dict(clarification)
    augmented["display_title"] = display_title_for_clarification(clarification)
    return augmented


def _finalize_ui_output(output: Dict) -> Dict:
    """Attach additive, backward-compatible display fields to an assembled
    UI output dict: `meta.status_display` and, on each clarification entry,
    `display_title`. Existing keys (`meta.status`, `clarifications[i].title`,
    `clarifications[i].requirement`, etc.) are left completely untouched --
    this only adds new keys for applicant-facing rendering to prefer."""
    meta = output.get("meta")
    if isinstance(meta, dict):
        meta["status_display"] = humanize_status(meta.get("status"))

    clarifications = output.get("clarifications")
    if isinstance(clarifications, list):
        output["clarifications"] = [_with_display_title(c) for c in clarifications]

    return output


def _load_pathway_json(relative_path: Optional[str]) -> Optional[Dict]:
    if not relative_path:
        return None
    try:
        path = Path(__file__).resolve().parent / relative_path
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_spain_dnv_output() -> Optional[Dict]:
    try:
        return json.loads(SPAIN_DNV_OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_spain_dnv_clarifications() -> Dict:
    try:
        return json.loads(SPAIN_DNV_CLARIFICATIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _first_requirement_variant(taxonomy_section: Dict, failed_requirements: List[str]) -> Optional[Dict]:
    variants = taxonomy_section.get("requirement_variants", {})
    if not isinstance(variants, dict):
        return None

    for requirement in failed_requirements:
        variant = variants.get(requirement)
        if isinstance(variant, dict):
            return variant
    return None


def _build_pathway_output(
    result: Dict,
    output_taxonomy: Dict,
    clarification_taxonomy: Dict,
) -> Dict:
    status = result.get("eligibility_status")
    work_type = result.get("work_type")
    visa_type = result.get("visa_type")
    failed_requirements: List[str] = result.get("failed_requirements", [])

    summary_tax = output_taxonomy.get("summary_statement", {})
    summary_variant = _first_requirement_variant(summary_tax, failed_requirements)
    if not summary_variant:
        summary_variant = summary_tax.get("variants", {}).get(status, {})

    cta_tax = output_taxonomy.get("next_steps_cta", {})
    cta_variant = _first_requirement_variant(cta_tax, failed_requirements)
    if not cta_variant:
        cta_variant = cta_tax.get("variants", {}).get(status)

    clarification_by_requirement = {
        item.get("requirement"): item
        for item in clarification_taxonomy.get("clarifications", [])
        if isinstance(item, dict) and item.get("requirement")
    }
    clarifications = [
        clarification_by_requirement[requirement]
        for requirement in failed_requirements
        if requirement in clarification_by_requirement
    ]
    if status == "needs_review" and not clarifications:
        manual_review = clarification_by_requirement.get("needs_manual_review")
        if manual_review:
            clarifications.append(manual_review)

    output: Dict = {
        "meta": {
            "status": status,
            "work_type": work_type,
            "visa_type": visa_type,
        },
        "summary": summary_variant.get("text", "") if isinstance(summary_variant, dict) else "",
        "clarifications": clarifications,
    }

    if isinstance(cta_variant, dict) and cta_variant.get("enabled"):
        output["next_steps"] = cta_variant

    return _finalize_ui_output(output)


def _build_spain_dnv_output(result: Dict, output_taxonomy: Dict) -> Dict:
    return _build_pathway_output(
        result,
        output_taxonomy,
        _load_spain_dnv_clarifications(),
    )


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
    pathway = result.get("pathway")

    if pathway:
        pathway_definition = resolve_pathway(pathway)
        pathway_output = _load_pathway_json(pathway_definition.output_file)
        if pathway_output:
            return _build_pathway_output(
                result,
                pathway_output,
                _load_pathway_json(pathway_definition.clarifications_file) or {},
            )

    if visa_type == "Spain Digital Nomad Visa":
        spain_output = _load_spain_dnv_output()
        if spain_output:
            return _build_spain_dnv_output(result, spain_output)

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

    return _finalize_ui_output(output)
