# evaluator engine (incremental)

from __future__ import annotations

from typing import Any, Dict, List, Optional


# --- Proto-taxonomy (in-code field spec) ---
# Order here is authoritative for deterministic missing_fields.
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


def evaluate(payload: Dict[str, Any]) -> dict:
    """Evaluator v0.1 (proto-taxonomy driven).

    Implements:
    - Deterministic missing_fields via FIELD_SPECS order
    - Direct depends_on enforcement (no transitive expansion)
    - Missing semantics: absent or None only
    - next_field_key = first visible missing field whose depends_on are satisfied
    """

    # Only read known sections (unknown keys ignored by construction)
    safe_payload: Dict[str, Any] = {
        "routing": payload.get("routing", {}) if isinstance(payload.get("routing", {}), dict) else {},
        "identity": payload.get("identity", {}) if isinstance(payload.get("identity", {}), dict) else {},
    }

    # 1) Compute missing_fields (ordered, deduped)
    missing_fields: List[str] = []

    # Build a quick map for declared order lookup
    declared_order = [s["key"] for s in FIELD_SPECS]
    declared_pos = {k: i for i, k in enumerate(declared_order)}

    def _add_missing(key: str) -> None:
        if key not in missing_fields:
            missing_fields.append(key)

    for spec in FIELD_SPECS:
        key = spec["key"]
        depends_on: List[str] = list(spec.get("depends_on") or [])

        # External-captured identity fields (e.g., Gravity Forms) are only
        # considered missing if the key exists AND value is None.
        value = _get_dotted(safe_payload, key)

        is_external_identity = key in ("identity.full_name", "identity.email")

        if is_external_identity:
            # If key is absent, do NOT treat as missing (engine does not own capture)
            if value is _MISSING:
                continue
            if value is None:
                _add_missing(key)
            continue

        # Standard engine-owned missing semantics
        if _is_missing(value):
            for dep in depends_on:
                dep_val = _get_dotted(safe_payload, dep)
                if _is_missing(dep_val):
                    _add_missing(dep)
            _add_missing(key)

    # Enforce declared ordering among missing fields (stable)
    missing_fields.sort(key=lambda k: declared_pos.get(k, 10**9))

    # 2) Select next_field_key deterministically
    next_field_key: Optional[str] = None

    for key in missing_fields:
        spec = next((s for s in FIELD_SPECS if s["key"] == key), None)
        if spec is None:
            continue

        if not _applies_when_true(safe_payload, spec):
            continue

        deps: List[str] = list(spec.get("depends_on") or [])
        # Only allow selection if dependencies are satisfied (provided)
        deps_satisfied = True
        for dep in deps:
            dep_val = _get_dotted(safe_payload, dep)
            if _is_missing(dep_val):
                deps_satisfied = False
                break

        if deps_satisfied:
            next_field_key = key
            break

    return {
        "eligibility_status": "Needs Review",
        "rule_results": [],
        "missing_fields": missing_fields,
        "next_field_key": next_field_key,
        "disclaimer_text": "stub",
    }
