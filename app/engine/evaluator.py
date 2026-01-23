# evaluator engine (clean, fixed)

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
from pathlib import Path

# -----------------------------
# Helpers / Sentinels
# -----------------------------

class _MissingType:
    pass

_MISSING = _MissingType()


def _get_dotted(payload: Dict[str, Any], dotted_key: str) -> Any:
    cur: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _is_missing(value: Any) -> bool:
    return value is _MISSING or value is None


def _applies_when_true(_payload: Dict[str, Any], _spec: Dict[str, Any]) -> bool:
    return True


# -----------------------------
# Taxonomy loader
# -----------------------------

FIELD_SPECS: List[Dict[str, Any]] = []


def _load_taxonomy_specs(work_relationship: Optional[str]) -> List[Dict[str, Any]]:
    if not work_relationship:
        return FIELD_SPECS

    tax_path = Path(__file__).resolve().parent / "taxonomies" / f"taxonomy_{work_relationship}.json"

    if not tax_path.exists():
        return FIELD_SPECS

    try:
        data = json.loads(tax_path.read_text(encoding="utf-8"))
        fields = data.get("taxonomy_fields", [])
        specs: List[Dict[str, Any]] = []
        for f in fields:
            if not isinstance(f, dict):
                continue
            key = f.get("key")
            if not isinstance(key, str):
                continue
            specs.append({
                "key": key,
                "depends_on": list(f.get("depends_on") or []),
                "applies_when": f.get("applies_when"),
                "label": f.get("label"),
                "input_type": f.get("input_type"),
                "choices": f.get("choices"),
            })
        return specs
    except Exception:
        return FIELD_SPECS


# -----------------------------
# Evaluator
# -----------------------------

def evaluate(payload: Dict[str, Any]) -> Dict[str, Any]:
    safe_payload = payload if isinstance(payload, dict) else {}

    for k in ("routing", "identity", "role", "income"):
        if not isinstance(safe_payload.get(k), dict):
            safe_payload[k] = {}

    # HARD GATE 1: work relationship
    if _is_missing(_get_dotted(safe_payload, "routing.work_relationship")):
        return {
            "missing_fields": ["routing.work_relationship"],
            "next_field_key": "routing.work_relationship",
            "field": {
                "label": "What best describes your work relationship?",
                "input_type": "choice",
                "choices": ["contractor", "employee", "business_owner"],
            },
        }

    # HARD GATE 2: applicant type
    if _is_missing(_get_dotted(safe_payload, "routing.applicant_type")):
        return {
            "missing_fields": ["routing.applicant_type"],
            "next_field_key": "routing.applicant_type",
            "field": {
                "label": "Are you applying as an individual or with family dependents?",
                "input_type": "choice",
                "choices": ["individual", "family"],
            },
        }

    # TAXONOMY LOOP
    specs = _load_taxonomy_specs(safe_payload["routing"].get("work_relationship"))

    missing_fields: List[str] = []
    spec_used: Optional[Dict[str, Any]] = None

    for spec in specs:
        key = spec["key"]

        if key.startswith("routing.dependent") or key == "routing.dependents_count":
            if safe_payload["routing"].get("applicant_type") != "family":
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

    # FIELD METADATA (NO LABEL INVENTION)
    field: Dict[str, Any] = {"input_type": "text"}

    ROUTING_DEFAULTS = {
        "routing.income_foreign_only": {"input_type": "choice", "choices": ["yes", "no"]},
        "routing.health_insurance_status": {"input_type": "choice", "choices": ["have", "will_obtain"]},
        "routing.background_check_available": {"input_type": "choice", "choices": ["yes", "no"]},
        "routing.criminal_record_flag": {"input_type": "choice", "choices": ["yes", "no"]},
        "role.business_owner.income_evidence_types": {
            "input_type": "choice",
            "choices": ["bank_statements", "invoices", "contracts", "tax_returns"],
        },
        "role.contractor.income_evidence_types": {
            "input_type": "choice",
            "choices": ["bank_statements", "invoices", "contracts"],
        },
        "role.employee.income_evidence_types": {
            "input_type": "choice",
            "choices": ["paystubs", "employment_letter", "bank_statements"],
        },
    }

    if next_field_key in ROUTING_DEFAULTS:
        field.update(ROUTING_DEFAULTS[next_field_key])

    if spec_used:
        if isinstance(spec_used.get("label"), str) and spec_used["label"].strip():
            field["label"] = spec_used["label"].strip()
        if isinstance(spec_used.get("input_type"), str) and spec_used["input_type"].strip():
            field["input_type"] = spec_used["input_type"].strip()
        if isinstance(spec_used.get("choices"), list) and spec_used["choices"]:
            field["choices"] = spec_used["choices"]

    return {
        "missing_fields": missing_fields,
        "next_field_key": next_field_key,
        "field": field,
    }
