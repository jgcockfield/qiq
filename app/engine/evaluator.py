# evaluator engine (clean, fixed)

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
from pathlib import Path

from app.engine.pathway_registry import CURRENT_BEHAVIOR, resolve_pathway

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


def _as_values(value: Any) -> List[Any]:
    if value is _MISSING or value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [value]


def _applies_when_true(payload: Dict[str, Any], spec: Dict[str, Any]) -> bool:
    condition = spec.get("applies_when")
    if not isinstance(condition, dict) or not condition:
        return True

    if "equals" in condition:
        key, expected = condition["equals"]
        return _get_dotted(payload, key) == expected

    if "not_equals" in condition:
        key, expected = condition["not_equals"]
        return _get_dotted(payload, key) != expected

    if "contains" in condition:
        key, expected = condition["contains"]
        return expected in _as_values(_get_dotted(payload, key))

    if "not_contains" in condition:
        key, expected = condition["not_contains"]
        return expected not in _as_values(_get_dotted(payload, key))

    return True


# -----------------------------
# Taxonomy loader
# -----------------------------

FIELD_SPECS: List[Dict[str, Any]] = []
PATHWAYS_BY_COUNTRY = {
    "spain": ["spain_dnv"],
    "costa_rica": ["costa_rica_dnv", "costa_rica_pensionado"],
}


def _spec_from_field(field: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    key = field.get("key")
    if not isinstance(key, str):
        return None

    return {
        "key": key,
        "depends_on": list(field.get("depends_on") or []),
        "applies_when": field.get("applies_when"),
        "label": field.get("label"),
        "description": field.get("description"),
        "input_type": field.get("input_type"),
        "choices": field.get("choices"),
        "required": field.get("required", True),
        "hidden": field.get("hidden", False),
        "typeform_field_id": field.get("typeform_field_id"),
        "typeform_ref": field.get("typeform_ref"),
    }


def _load_taxonomy_file(tax_path: Path) -> List[Dict[str, Any]]:
    if not tax_path.exists():
        return FIELD_SPECS

    try:
        data = json.loads(tax_path.read_text(encoding="utf-8"))
        fields = data.get("taxonomy_fields", [])
        specs: List[Dict[str, Any]] = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            spec = _spec_from_field(field)
            if spec:
                specs.append(spec)
        return specs
    except Exception:
        return FIELD_SPECS


def _load_taxonomy_specs(work_relationship: Optional[str]) -> List[Dict[str, Any]]:
    if not work_relationship:
        return FIELD_SPECS

    tax_path = Path(__file__).resolve().parent / "taxonomies" / f"taxonomy_{work_relationship}.json"
    return _load_taxonomy_file(tax_path)

def _load_pathway_taxonomy_specs(questions_file: Optional[str]) -> List[Dict[str, Any]]:
    if not questions_file:
        return FIELD_SPECS

    tax_path = Path(__file__).resolve().parent / questions_file
    return _load_taxonomy_file(tax_path)


def _legacy_applicant_type_regression_result(
    safe_payload: Dict[str, Any],
    pathway_was_omitted: bool,
) -> Optional[Dict[str, Any]]:
    if not pathway_was_omitted:
        return None
    if safe_payload["routing"].get("work_relationship") != "contractor":
        return None
    if _is_missing(_get_dotted(safe_payload, "income.monthly_amount")):
        return None
    if not _is_missing(_get_dotted(safe_payload, "role.contractor.monthly_income_usd")):
        return None

    applicant_type = safe_payload["routing"].get("applicant_type")
    thresholds = {
        "individual": 3000,
        "family": 4000,
    }
    threshold = thresholds.get(applicant_type)

    if threshold is None:
        rule_status = "needs_review"
        reason = "Applicant type threshold not available."
    else:
        try:
            monthly_amount = float(_get_dotted(safe_payload, "income.monthly_amount"))
        except (TypeError, ValueError):
            monthly_amount = 0
        rule_status = "pass" if monthly_amount >= threshold else "fail"
        reason = None

    rule_result = {
        "rule_id": "DN_MIN_MONTHLY_INCOME",
        "status": rule_status,
    }
    if reason:
        rule_result["reason"] = reason

    return {
        "missing_fields": [],
        "next_field_key": None,
        "rule_results": [rule_result],
    }


def _stage_one_selector_result(safe_payload: Dict[str, Any], selected_pathway: Optional[str]) -> Optional[Dict[str, Any]]:
    if selected_pathway:
        return None
    if safe_payload["routing"].get("work_relationship"):
        return None

    country = safe_payload["routing"].get("country")
    if _is_missing(_get_dotted(safe_payload, "routing.country")):
        return {
            "missing_fields": ["routing.country"],
            "next_field_key": "routing.country",
            "field": {
                "label": "Which country are you interested in?",
                "input_type": "choice",
                "choices": ["spain", "costa_rica"],
            },
        }

    pathway_choices = PATHWAYS_BY_COUNTRY.get(country, [])
    if _is_missing(_get_dotted(safe_payload, "routing.pathway")):
        return {
            "missing_fields": ["routing.pathway"],
            "next_field_key": "routing.pathway",
            "field": {
                "label": "Which pathway would you like to check?",
                "input_type": "choice",
                "choices": pathway_choices,
            },
        }

    return None


def _next_missing_from_specs(
    safe_payload: Dict[str, Any],
    specs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    missing_fields: List[str] = []
    spec_used: Optional[Dict[str, Any]] = None

    for spec in specs:
        if spec.get("required") is False:
            continue

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
        if isinstance(spec_used.get("description"), str) and spec_used["description"].strip():
            field["description"] = spec_used["description"].strip()
        if isinstance(spec_used.get("input_type"), str) and spec_used["input_type"].strip():
            field["input_type"] = spec_used["input_type"].strip()
        if isinstance(spec_used.get("choices"), list) and spec_used["choices"]:
            field["choices"] = spec_used["choices"]
        if isinstance(spec_used.get("typeform_field_id"), str):
            field["typeform_field_id"] = spec_used["typeform_field_id"]
        if isinstance(spec_used.get("typeform_ref"), str):
            field["typeform_ref"] = spec_used["typeform_ref"]

    return {
        "missing_fields": missing_fields,
        "next_field_key": next_field_key,
        "field": field,
    }


# -----------------------------
# Evaluator
# -----------------------------

def evaluate(payload: Dict[str, Any], pathway: Optional[str] = None) -> Dict[str, Any]:
    safe_payload = payload if isinstance(payload, dict) else {}

    for k in ("routing", "identity", "role", "income"):
        if not isinstance(safe_payload.get(k), dict):
            safe_payload[k] = {}

    selected_pathway = pathway or safe_payload.get("pathway") or safe_payload["routing"].get("pathway")
    pathway_was_omitted = not selected_pathway

    stage_one_result = _stage_one_selector_result(safe_payload, selected_pathway)
    if stage_one_result:
        return stage_one_result

    pathway_definition = resolve_pathway(selected_pathway)

    # Phase 1: only the current Costa Rica behavior is implemented.
    # Placeholder pathways are registered for future dispatch without changing
    # existing navigation behavior yet.
    if pathway_definition.behavior != CURRENT_BEHAVIOR:
        pass

    pathway_specs = _load_pathway_taxonomy_specs(pathway_definition.questions_file)
    if pathway_specs:
        return _next_missing_from_specs(safe_payload, pathway_specs)

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

    legacy_result = _legacy_applicant_type_regression_result(
        safe_payload,
        pathway_was_omitted,
    )
    if legacy_result:
        return legacy_result

    # TAXONOMY LOOP
    specs = _load_taxonomy_specs(safe_payload["routing"].get("work_relationship"))
    return _next_missing_from_specs(safe_payload, specs)
