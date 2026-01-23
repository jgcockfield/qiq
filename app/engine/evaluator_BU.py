# evaluator engine (incremental)

from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
from pathlib import Path


# --- Proto-taxonomy (in-code field spec) ---
# Fallback only. Real taxonomies are loaded from app/engine/taxonomies/.
FIELD_SPECS: List[Dict[str, Any]] = [
    {
        "key": "identity.full_name",
        "depends_on": [],
        "applies_when": None,  # placeholder; always true for now
    },
    {
        "key": "identity.email",
        "depends_on": [],
        "applies_when": None,
    },
    {
        "key": "identity.nationality",
        "depends_on": ["identity.full_name"],
        "applies_when": None,
    },
]


def _get_dotted(payload: Dict[str, Any], dotted_key: str) -> Any:
    """Get a value by dotted path. Returns a sentinel for missing keys."""
    cur: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


# Sentinel for key-absence (distinct from None)
class _MissingType:
    pass


_MISSING = _MissingType()


def _is_missing(value: Any) -> bool:
    """Missing semantics:
    - Missing if key is absent OR value is None
    - Empty string / 0 / False / empty list / empty dict are PROVIDED
    """
    return value is _MISSING or value is None


def _applies_when_true(_payload: Dict[str, Any], _spec: Dict[str, Any]) -> bool:
    # Placeholder until applies_when is wired via JSONLogic.
    return True


def _load_taxonomy_specs(work_relationship: Optional[str]) -> List[Dict[str, Any]]:
    """Load taxonomy specs from disk for the active work_relationship.

    Contract (Build 2):
    - Path: app/engine/taxonomies/taxonomy_{work_relationship}.json
    - Field order is preserved from taxonomy_fields array order.
    - If file missing/unreadable, fall back to FIELD_SPECS.
    """
    if not work_relationship:
        return FIELD_SPECS

    tax_path = Path(__file__).resolve().parent / "taxonomies" / f"taxonomy_{work_relationship}.json"
    if not tax_path.exists():
        return FIELD_SPECS

    try:
        data = json.loads(tax_path.read_text(encoding="utf-8"))
        fields = data.get("taxonomy_fields", [])
        if not isinstance(fields, list):
            return FIELD_SPECS

        specs: List[Dict[str, Any]] = []
        for f in fields:
            if not isinstance(f, dict):
                continue
            key = f.get("key")
            if not isinstance(key, str) or not key:
                continue
            specs.append(
                {
                    "key": key,
                    "depends_on": list(f.get("depends_on") or []),
                    "applies_when": f.get("applies_when"),
                    "label": f.get("label"),
                    "choices": f.get("choices"),
                    "input_type": f.get("input_type"),
                }
            )
        return specs or FIELD_SPECS
    except Exception:
        return FIELD_SPECS


def evaluate(payload: Dict[str, Any]) -> dict:
    """Evaluator v0.1 (proto-taxonomy driven)."""

    safe_payload: Dict[str, Any] = payload if isinstance(payload, dict) else {}

    if not isinstance(safe_payload.get("routing"), dict):
        safe_payload["routing"] = {}
    if not isinstance(safe_payload.get("identity"), dict):
        safe_payload["identity"] = {}
    if not isinstance(safe_payload.get("income"), dict):
        safe_payload["income"] = {}
    if not isinstance(safe_payload.get("role"), dict):
        safe_payload["role"] = {}

    # --- HARD GATE: routing.work_relationship must be asked first ---
    if _is_missing(_get_dotted(safe_payload, "routing.work_relationship")):
        return {
            "missing_fields": ["routing.work_relationship"],
            "next_field_key": "routing.work_relationship",
            "field": {
                "label": "What best describes your work relationship?",
                "choices": ["contractor", "employee", "business_owner"],
                "input_type": "choice",
            },
        }

    # --- HARD GATE: routing.applicant_type ---
    if _is_missing(_get_dotted(safe_payload, "routing.applicant_type")):
        return {
            "missing_fields": ["routing.applicant_type"],
            "next_field_key": "routing.applicant_type",
            "field": {
                "label": "Are you applying as an individual or with family dependents?",
                "choices": ["individual", "family"],
                "input_type": "choice",
            },
        }

    # --- HARD GATE: routing.income_foreign_only ---
    if _is_missing(_get_dotted(safe_payload, "routing.income_foreign_only")):
        return {
            "missing_fields": ["routing.income_foreign_only"],
            "next_field_key": "routing.income_foreign_only",
            "field": {
                "label": "Is all of your income sourced from outside Costa Rica?",
                "choices": ["yes", "no"],
                "input_type": "choice",
            },
        }

    # --- HARD GATE: role.contractor.monthly_income_usd ---
    if safe_payload.get("routing", {}).get("work_relationship") == "contractor" and _is_missing(_get_dotted(safe_payload, "role.contractor.monthly_income_usd")):
        return {
            "missing_fields": ["role.contractor.monthly_income_usd"],
            "next_field_key": "role.contractor.monthly_income_usd",
            "field": {
                "label": "What is your average gross monthly contract income (USD)?",
                "input_type": "number",
            },
        }

    # --- HARD GATE: role.contractor.income_evidence_types ---
    if (
        safe_payload.get("routing", {}).get("work_relationship") == "contractor"
        and _is_missing(_get_dotted(safe_payload, "role.contractor.income_evidence_types"))
    ):
        return {
            "missing_fields": ["role.contractor.income_evidence_types"],
            "next_field_key": "role.contractor.income_evidence_types",
            "field": {
                "label": "Which documents can you provide as proof of your contractor income?",
                "choices": [
                    "bank_statements",
                    "invoices",
                    "contracts",
                    "tax_returns",
                    "other",
                ],
                "input_type": "multi_choice",
            },
        }

    # --- HARD GATE: role.contractor.income_evidence_months ---
    if safe_payload.get("routing", {}).get("work_relationship") == "contractor" and _is_missing(_get_dotted(safe_payload, "role.contractor.income_evidence_months")):
        return {
            "missing_fields": ["role.contractor.income_evidence_months"],
            "next_field_key": "role.contractor.income_evidence_months",
            "field": {
                "label": "For how many months can you prove this income with those documents?",
                "choices": ["3", "6", "9", "12"],
                "input_type": "choice",
            },
        }

    # --- HARD GATE: routing.dependents_count (family only) ---
    if safe_payload.get("routing", {}).get("applicant_type") == "family" and _is_missing(_get_dotted(safe_payload, "routing.dependents_count")):
        return {
            "missing_fields": ["routing.dependents_count"],
            "next_field_key": "routing.dependents_count",
            "field": {
                "label": "How many dependents are included in your application?",
                "input_type": "number",
            },
        }

    # --- HARD GATE: routing.dependent_relationships (family only) ---
    if safe_payload.get("routing", {}).get("applicant_type") == "family" and _is_missing(_get_dotted(safe_payload, "routing.dependent_relationships")):
        return {
            "missing_fields": ["routing.dependent_relationships"],
            "next_field_key": "routing.dependent_relationships",
            "field": {
                "label": "What is each dependentâ€™s relationship to you?",
                "input_type": "text",
            },
        }

    # --- HARD GATE: routing.dependent_ages (family only) ---
    if safe_payload.get("routing", {}).get("applicant_type") == "family" and _is_missing(_get_dotted(safe_payload, "routing.dependent_ages")):
        return {
            "missing_fields": ["routing.dependent_ages"],
            "next_field_key": "routing.dependent_ages",
            "field": {
                "label": "What is the age of each dependent?",
                "input_type": "text",
            },
        }

    # --- HARD GATE: identity.nationality ---
    if _is_missing(_get_dotted(safe_payload, "identity.nationality")):
        return {
            "missing_fields": ["identity.nationality"],
            "next_field_key": "identity.nationality",
            "field": {
                "label": "What is your nationality?",
                "input_type": "text",
            },
        }

    # --- HARD GATE: routing.passport_validity_months ---
    if _is_missing(_get_dotted(safe_payload, "routing.passport_validity_months")):
        return {
            "missing_fields": ["routing.passport_validity_months"],
            "next_field_key": "routing.passport_validity_months",
            "field": {
                "label": "How many months will your passport be valid from your intended entry date?",
                "input_type": "number",
            },
        }

    # --- HARD GATE: routing.health_insurance_status ---
    if _is_missing(_get_dotted(safe_payload, "routing.health_insurance_status")):
        return {
            "missing_fields": ["routing.health_insurance_status"],
            "next_field_key": "routing.health_insurance_status",
            "field": {
                "label": "Do you have qualifying health insurance for Costa Rica, or will you obtain it?",
                "choices": ["have_it", "will_obtain"],
                "input_type": "choice",
            },
        }

    # --- HARD GATE: routing.background_check_available ---
    if _is_missing(_get_dotted(safe_payload, "routing.background_check_available")):
        return {
            "missing_fields": ["routing.background_check_available"],
            "next_field_key": "routing.background_check_available",
            "field": {
                "label": "Can you obtain a criminal background check from your country of residence?",
                "choices": ["yes", "no"],
                "input_type": "choice",
            },
        }

    # --- HARD GATE: routing.criminal_record_flag ---
    if _is_missing(_get_dotted(safe_payload, "routing.criminal_record_flag")):
        return {
            "missing_fields": ["routing.criminal_record_flag"],
            "next_field_key": "routing.criminal_record_flag",
            "field": {
                "label": "Do you have any criminal convictions that may appear on your background check?",
                "choices": ["yes", "no"],
                "input_type": "choice",
            },
        }

    # --- TAXONOMY-DRIVEN FIELDS ---
    # NOTE: dependents fields must be skipped unless applicant_type == 'family'
    specs = _load_taxonomy_specs(safe_payload.get("routing", {}).get("work_relationship"))

    missing_fields: List[str] = []
    spec_used: Optional[Dict[str, Any]] = None

    for spec in specs:
        key = spec["key"]

        # Skip dependents fields unless family
        if key.startswith("routing.dependent") or key == "routing.dependents_count":
            if safe_payload.get("routing", {}).get("applicant_type") != "family":
                continue

        # Skip legacy/mistaken key (nationality lives under identity.*)
        if key == "routing.nationality":
            continue
        if not _applies_when_true(safe_payload, spec):
            continue
        if _is_missing(_get_dotted(safe_payload, key)):
            missing_fields.append(key)
            spec_used = spec
            break

    if not missing_fields:
        return {"missing_fields": [], "next_field_key": None}

    next_field_key = missing_fields[0]

    # --- FIELD METADATA (taxonomy-first; fallback to key prettify) ---
    field: Dict[str, Any] = {
        "label": next_field_key.replace(".", " ").replace("_", " ").title(),
        "input_type": "text",
    }

    if spec_used:
        if isinstance(spec_used.get("label"), str) and spec_used["label"].strip():
            field["label"] = spec_used["label"].strip()
        if isinstance(spec_used.get("input_type"), str) and spec_used["input_type"].strip():
            field["input_type"] = spec_used["input_type"].strip()
        choices = spec_used.get("choices")
        if isinstance(choices, list) and choices:
            field["choices"] = choices

    return {
        "missing_fields": missing_fields,
        "next_field_key": next_field_key,
        "field": field,
    }