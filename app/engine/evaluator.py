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
    """Evaluator v0.1 (proto-taxonomy driven).

    Implements:
    - Deterministic missing_fields via FIELD_SPECS order
    - Direct depends_on enforcement (no transitive expansion)
    - Missing semantics: absent or None only
    - next_field_key = first visible missing field whose depends_on are satisfied
    """

    # Only read known sections (unknown keys ignored by construction)
    safe_payload: Dict[str, Any] = payload if isinstance(payload, dict) else {}

    # Normalize critical roots to dicts
    if not isinstance(safe_payload.get("routing"), dict):
        safe_payload["routing"] = {}
    if not isinstance(safe_payload.get("identity"), dict):
        safe_payload["identity"] = {}
    if not isinstance(safe_payload.get("income"), dict):
        safe_payload["income"] = {}
    if not isinstance(safe_payload.get("role"), dict):
        safe_payload["role"] = {}


    # 1) Compute missing_fields (ordered, deduped)
    missing_fields: List[str] = []

    work = safe_payload.get("routing", {}).get("work_relationship")
    active_specs = _load_taxonomy_specs(work)

    # Build a quick map for declared order lookup
    declared_order = [s["key"] for s in active_specs]
    declared_pos = {k: i for i, k in enumerate(declared_order)}

    def _add_missing(key: str) -> None:
        if key not in missing_fields:
            missing_fields.append(key)

    for spec in active_specs:
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
        spec = next((s for s in active_specs if s["key"] == key), None)
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

    # --- Phase 2: Overlay Rule Execution (deterministic) ---
    # NOTE: This block must not alter Phase 1 missing_fields logic or ordering.
    # It evaluates overlay rules against the raw payload (not safe_payload), then
    # computes eligibility_status deterministically.

    def _load_overlay(work_relationship: Optional[str]) -> Dict[str, Any]:
        if not work_relationship:
            raise ValueError("work_relationship missing")

        overlay_path = Path(__file__).resolve().parent / "overlays" / f"overlay_{work_relationship}.json"
        if not overlay_path.exists():
            raise FileNotFoundError(f"overlay not found: {overlay_path}")

        data = json.loads(overlay_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("overlay root must be an object")

        # Minimal compatibility checks (fail closed if incompatible)
        rules = data.get("rules")
        if not isinstance(rules, list):
            raise TypeError("overlay.rules must be a list")

        for r in rules:
            if not isinstance(r, dict):
                raise TypeError("rule must be an object")
            rid = r.get("rule_id")
            if not isinstance(rid, str) or not rid:
                raise ValueError("rule.rule_id missing/invalid")
            field_keys = r.get("field_keys")
            if not isinstance(field_keys, list) or not all(isinstance(k, str) and k for k in field_keys):
                raise ValueError(f"rule {rid}: field_keys missing/invalid")
            test = r.get("test")
            if not isinstance(test, str) or not test:
                raise ValueError(f"rule {rid}: test missing/invalid")

        return data

    def _missing_keys(rule_payload: Dict[str, Any], keys: List[str]) -> List[str]:
        missing: List[str] = []
        for k in keys:
            v = _get_dotted(rule_payload, k)
            if _is_missing(v):
                missing.append(k)
        return missing

    def _as_number(v: Any) -> Optional[float]:
        if isinstance(v, (int, float)):
            return float(v)
        return None

    def _evaluate_rule(rule_payload: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, str]:
        rid = str(rule.get("rule_id"))
        field_keys: List[str] = list(rule.get("field_keys") or [])
        test = str(rule.get("test"))
        fail_outcome = rule.get("fail_outcome", "needs_review")
        user_meaning = rule.get("user_facing_meaning")
        if not isinstance(user_meaning, str) or not user_meaning:
            user_meaning = "Rule evaluated."

        missing = _missing_keys(rule_payload, field_keys)
        if missing:
            return {
                "rule_id": rid,
                "status": "needs_review",
                "reason": f"Missing required field(s): {', '.join(missing)}.",
            }

        # Helper to map a failing rule to deterministic status
        def _fail_status() -> str:
            return "fail" if fail_outcome == "ineligible" else "needs_review"

        # Test implementations (deterministic)
        if test == "equals":
            v = _get_dotted(rule_payload, field_keys[0])
            target = rule.get("pass")
            if v == target:
                return {"rule_id": rid, "status": "pass", "reason": user_meaning}
            return {"rule_id": rid, "status": _fail_status(), "reason": user_meaning}

        if test == "not_equals":
            v = _get_dotted(rule_payload, field_keys[0])
            target = rule.get("pass")
            if v != target:
                return {"rule_id": rid, "status": "pass", "reason": user_meaning}
            return {"rule_id": rid, "status": _fail_status(), "reason": user_meaning}

        if test == "gte_number":
            v_num = _as_number(_get_dotted(rule_payload, field_keys[0]))
            threshold = _as_number(rule.get("pass"))
            if v_num is None or threshold is None:
                return {"rule_id": rid, "status": "needs_review", "reason": "Numeric comparison not evaluable."}
            if v_num >= threshold:
                return {"rule_id": rid, "status": "pass", "reason": user_meaning}
            return {"rule_id": rid, "status": _fail_status(), "reason": user_meaning}

        if test == "gte_threshold_by_applicant_type":
            income_val = _as_number(_get_dotted(rule_payload, field_keys[0]))
            applicant_type = _get_dotted(rule_payload, field_keys[1])
            thresholds = rule.get("pass")
            if income_val is None or applicant_type is _MISSING or applicant_type is None:
                return {"rule_id": rid, "status": "needs_review", "reason": "Income/applicant type not evaluable."}
            if not isinstance(thresholds, dict) or applicant_type not in thresholds:
                return {"rule_id": rid, "status": "needs_review", "reason": "Applicant type threshold not available."}
            threshold_val = _as_number(thresholds.get(applicant_type))
            if threshold_val is None:
                return {"rule_id": rid, "status": "needs_review", "reason": "Applicant type threshold not evaluable."}
            if income_val >= threshold_val:
                return {"rule_id": rid, "status": "pass", "reason": user_meaning}
            return {"rule_id": rid, "status": _fail_status(), "reason": user_meaning}

        if test == "is_valid_at_application":
            # Locked rule: passport must be valid at time of application only.
            # Deterministic evaluation: provided (non-missing) => pass.
            return {"rule_id": rid, "status": "pass", "reason": user_meaning}

        if test == "requires_policy_check":
            # Deterministic: always needs_review once required field(s) are present.
            return {"rule_id": rid, "status": "needs_review", "reason": user_meaning}

        if test == "dgme_controlled_gate":
            # Deterministic: always needs_review once required field(s) are present.
            return {"rule_id": rid, "status": "needs_review", "reason": user_meaning}

        # Unknown test => fail closed at rule level
        return {"rule_id": rid, "status": "needs_review", "reason": f"Unsupported rule test: {test}."}

    # --- Phase 4: Deterministic Field Mapping (source -> canonical) ---
    # Runs BEFORE overlay rule evaluation. Does not modify missing_fields logic/order.

    def _set_dotted(obj: Dict[str, Any], dotted_key: str, value: Any) -> None:
        cur: Any = obj
        parts = dotted_key.split(".")
        for part in parts[:-1]:
            if part not in cur or not isinstance(cur.get(part), dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value

    def _apply_field_mappings(rule_payload: Dict[str, Any]) -> None:
        # M1 — Contractor monthly income
        # income.monthly_amount -> role.contractor.monthly_income_usd
        work_rel = _get_dotted(rule_payload, "routing.work_relationship")
        if work_rel != "contractor":
            return

        src = _get_dotted(rule_payload, "income.monthly_amount")
        if not _is_missing(src):
            tgt = _get_dotted(rule_payload, "role.contractor.monthly_income_usd")
            if _is_missing(tgt):
                _set_dotted(rule_payload, "role.contractor.monthly_income_usd", src)

        # M2 — Work relationship -> applicant type
        # routing.work_relationship -> routing.applicant_type
        src_wr = _get_dotted(rule_payload, "routing.work_relationship")
        tgt_at = _get_dotted(rule_payload, "routing.applicant_type")
        if not _is_missing(src_wr) and _is_missing(tgt_at):
            _set_dotted(rule_payload, "routing.applicant_type", src_wr)

        # M3 — Identity nationality -> routing nationality
        # identity.nationality -> routing.nationality
        src_nat = _get_dotted(rule_payload, "identity.nationality")
        tgt_nat = _get_dotted(rule_payload, "routing.nationality")
        if not _is_missing(src_nat) and _is_missing(tgt_nat):
            _set_dotted(rule_payload, "routing.nationality", src_nat)

    rule_results: List[Dict[str, str]] = []
    eligibility_status: str = "Needs Review"

    try:
        overlay = _load_overlay(work)
        rule_payload = payload if isinstance(payload, dict) else {}

        # Apply deterministic mappings before rule evaluation
        _apply_field_mappings(rule_payload)

        for r in overlay.get("rules", []):
            rule_results.append(_evaluate_rule(rule_payload, r))

        # Deterministic eligibility computation (overlay + Phase 1 completeness)
        if missing_fields:
            eligibility_status = "Needs Review"
        else:
            any_fail = any(rr.get("status") == "fail" for rr in rule_results)
            any_review = any(rr.get("status") == "needs_review" for rr in rule_results)
            if any_fail:
                eligibility_status = "Ineligible"
            elif any_review:
                eligibility_status = "Needs Review"
            else:
                eligibility_status = "Eligible"

    except Exception:
        # Fail closed on any overlay authority failure
        eligibility_status = "Needs Review"
        rule_results = [
            {
                "rule_id": "SYSTEM_AUTHORITY_FAILURE",
                "status": "needs_review",
                "reason": f"Overlay missing/invalid/incompatible for work_relationship={work}.",
            }
        ]

    return {
        "eligibility_status": eligibility_status,
        "rule_results": rule_results,
        "missing_fields": missing_fields,
        "next_field_key": next_field_key,
        "disclaimer_text": "stub",
    }
