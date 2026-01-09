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
        }

    missing_fields: List[str] = []

    work = safe_payload.get("routing", {}).get("work_relationship")
    active_specs = _load_taxonomy_specs(work)

    declared_order = [s["key"] for s in active_specs]
    declared_pos = {k: i for i, k in enumerate(declared_order)}

    def _add_missing(key: str) -> None:
        if key not in missing_fields:
            missing_fields.append(key)

    for spec in active_specs:
        key = spec["key"]
        depends_on: List[str] = list(spec.get("depends_on") or [])

        value = _get_dotted(safe_payload, key)

        is_external_identity = key in ("identity.full_name", "identity.email")

        if is_external_identity:
            if value is _MISSING:
                continue
            if value is None:
                _add_missing(key)
            continue

        if _is_missing(value):
            for dep in depends_on:
                # Never auto-add external identity fields as missing (Gravity Forms owns them)
                if dep in ("identity.full_name", "identity.email"):
                    continue
                dep_val = _get_dotted(safe_payload, dep)
                if _is_missing(dep_val):
                    _add_missing(dep)
            _add_missing(key)

    missing_fields.sort(key=lambda k: declared_pos.get(k, 10**9))

    next_field_key: Optional[str] = None

    for key in missing_fields:
        spec = next((s for s in active_specs if s["key"] == key), None)
        if spec is None:
            continue
        if not _applies_when_true(safe_payload, spec):
            continue
        deps: List[str] = list(spec.get("depends_on") or [])
        if all((d in ("identity.full_name", "identity.email")) or (not _is_missing(_get_dotted(safe_payload, d))) for d in deps):
            next_field_key = key
            break

    return {
        "missing_fields": missing_fields,
        "next_field_key": next_field_key,
    }
