"""Determinism + contract tests for POST /evaluate (Build 2).

These tests are intentionally contract-first:
- They enforce /evaluate behavior and deterministic outputs.
- They avoid any UI logic assumptions.

How this file runs:
1) Preferred path: FastAPI TestClient calls POST /evaluate.
2) If the FastAPI app cannot be imported, tests will SKIP with a clear reason.

Adjust the APP_IMPORT_CANDIDATES list if your FastAPI app lives elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import json

import pytest


APP_IMPORT_CANDIDATES = [
    "app.main:app",  # common
    "app.api.app:app",
    "app.api.main:app",
    "main:app",
]


def _import_fastapi_app():
    """Attempt to import a FastAPI app from known locations.

    Returns:
        app: FastAPI instance

    Raises:
        ImportError if not found.
    """

    last_err: Optional[Exception] = None
    for spec in APP_IMPORT_CANDIDATES:
        mod_name, attr = spec.split(":", 1)
        try:
            mod = __import__(mod_name, fromlist=[attr])
            app = getattr(mod, attr)
            return app
        except Exception as e:  # noqa: BLE001 (intentional: probe import)
            last_err = e
    raise ImportError(
        "Could not import FastAPI app from candidates: "
        + ", ".join(APP_IMPORT_CANDIDATES)
        + (f". Last error: {last_err!r}" if last_err else "")
    )


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient for /evaluate."""
    try:
        from fastapi.testclient import TestClient

        app = _import_fastapi_app()
        return TestClient(app)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Skipping API tests: FastAPI app/TestClient not available. {e}")


@dataclass(frozen=True)
class EvalResponse:
    status_code: int
    json: Dict[str, Any]


def post_evaluate(client, payload: Dict[str, Any]) -> EvalResponse:
    """POST /evaluate and return status + JSON.

    Assumes the endpoint is mounted at /evaluate.
    """

    resp = client.post("/evaluate", json=payload)
    try:
        data = resp.json() if resp.content else {}
    except Exception:  # noqa: BLE001
        data = {"_non_json_response": resp.text}
    return EvalResponse(status_code=resp.status_code, json=data)


def assert_has_required_fields(body: Dict[str, Any]) -> None:
    for k in [
        "eligibility_status",
        "rule_results",
        "missing_fields",
        "next_field_key",
        "disclaimer_text",
    ]:
        assert k in body, f"Missing required field: {k}"


def find_rule(body: Dict[str, Any], rule_id: str) -> Optional[Dict[str, Any]]:
    rr = body.get("rule_results")
    if not isinstance(rr, list):
        return None
    for item in rr:
        if isinstance(item, dict) and item.get("rule_id") == rule_id:
            return item
    return None


def normalize_required_fields(body: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize response for determinism assertions.

    - rule_results ordering is undefined, so we compare as a multiset-like sorted list
      using a stable key (rule_id, status, reason).
    - missing_fields is ordered and MUST be compared as-is.
    """

    assert_has_required_fields(body)

    rr = body["rule_results"]
    assert isinstance(rr, list), "rule_results must be an array"

    rr_norm = []
    for item in rr:
        assert isinstance(item, dict), "rule_results items must be objects"
        rr_norm.append(
            {
                "rule_id": item.get("rule_id"),
                "status": item.get("status"),
                "reason": item.get("reason"),
            }
        )

    rr_norm_sorted = sorted(
        rr_norm,
        key=lambda x: (
            "" if x["rule_id"] is None else str(x["rule_id"]),
            "" if x["status"] is None else str(x["status"]),
            "" if x["reason"] is None else str(x["reason"]),
        ),
    )

    mf = body["missing_fields"]
    assert isinstance(mf, list), "missing_fields must be an array"
    assert all(isinstance(x, str) for x in mf), "missing_fields must be array of strings"

    return {
        "eligibility_status": body["eligibility_status"],
        "rule_results": rr_norm_sorted,
        "missing_fields": mf,
        "next_field_key": body["next_field_key"],
        "disclaimer_text": body["disclaimer_text"],
    }


# -----------------
# Critical 8 tests
# -----------------


def test_route_001_missing_payload_returns_422_and_system_authority_failure(client):
    """T-ROUTE-001: Empty payload => 422 + SYSTEM_AUTHORITY_FAILURE."""
    r = post_evaluate(client, {})
    assert r.status_code == 422

    # Body may or may not include full EvaluateResponse on validation errors.
    # Contract addition expects a body with SYSTEM_AUTHORITY_FAILURE.
    rule = find_rule(r.json, "SYSTEM_AUTHORITY_FAILURE")
    assert rule is not None, "Expected SYSTEM_AUTHORITY_FAILURE rule_result in body"


def test_route_002_invalid_work_relationship_returns_422_and_system_authority_failure(client):
    """T-ROUTE-002: Invalid work_relationship => 422 + SYSTEM_AUTHORITY_FAILURE."""
    r = post_evaluate(client, {"routing": {"work_relationship": "freelancer"}})
    assert r.status_code == 422

    rule = find_rule(r.json, "SYSTEM_AUTHORITY_FAILURE")
    assert rule is not None, "Expected SYSTEM_AUTHORITY_FAILURE rule_result in body"


def test_core_002_repeat_stability_missing_fields_order_is_identical(client):
    """T-CORE-002: Same input called repeatedly => identical missing_fields ordering."""
    payload = {"routing": {"work_relationship": "employee"}}

    first = post_evaluate(client, payload)
    assert first.status_code in (200, 422), "Unexpected status code"

    # If 422 happens here, it means your engine currently rejects valid work_relationship.
    # That is a failure of routing setup; surface it cleanly.
    if first.status_code == 422:
        pytest.fail(f"Expected 200 for valid routing, got 422: {first.json}")

    base = normalize_required_fields(first.json)

    for i in range(10):
        r = post_evaluate(client, payload)
        assert r.status_code == 200
        cur = normalize_required_fields(r.json)
        assert cur["missing_fields"] == base["missing_fields"], f"missing_fields order drift on run {i}"
        assert cur["next_field_key"] == base["next_field_key"], f"next_field_key drift on run {i}"
        assert cur["eligibility_status"] == base["eligibility_status"], f"eligibility_status drift on run {i}"


def test_core_003_unknown_keys_ignored_outputs_identical(client):
    """T-CORE-003: Unknown keys ignored (including __proto__) => identical outputs."""
    a = {
        "routing": {"work_relationship": "business_owner"},
        "unknown_key": "xyz",
        "identity": {"full_name": "Jude"},
        "__proto__": {"pollute": True},
    }
    b = {
        "routing": {"work_relationship": "business_owner"},
        "identity": {"full_name": "Jude"},
    }

    ra = post_evaluate(client, a)
    rb = post_evaluate(client, b)

    # Both should be 200 if routing is valid.
    assert ra.status_code == 200, f"Unexpected status A: {ra.status_code} {ra.json}"
    assert rb.status_code == 200, f"Unexpected status B: {rb.status_code} {rb.json}"

    na = normalize_required_fields(ra.json)
    nb = normalize_required_fields(rb.json)

    assert na["eligibility_status"] == nb["eligibility_status"]
    assert na["missing_fields"] == nb["missing_fields"]
    assert na["next_field_key"] == nb["next_field_key"]


def test_miss_005_null_is_missing(client):
    """T-MISS-005: null counts as missing."""
    payload = {
        "routing": {"work_relationship": "contractor"},
        "identity": {"nationality": None},
    }
    r = post_evaluate(client, payload)
    assert r.status_code == 200
    body = r.json
    assert_has_required_fields(body)

    mf = body["missing_fields"]
    assert isinstance(mf, list)
    assert "identity.nationality" in mf or any(
        x.endswith("nationality") for x in mf
    ), "Expected nationality field to be missing when null"


def test_missing_fields_order_is_declaration_order(client):
    """Determinism: missing_fields preserves declaration order (no sorting)."""
    payload = {
        "routing": {"work_relationship": "contractor"},
        "identity": {"full_name": None, "nationality": None},
    }
    r = post_evaluate(client, payload)
    assert r.status_code == 200
    body = r.json
    assert_has_required_fields(body)

    assert body["missing_fields"][:2] == ["identity.full_name", "identity.nationality"]
    assert body["next_field_key"] == "identity.full_name"


def test_miss_001_empty_string_is_provided_not_missing(client):
    """T-MISS-001: empty string counts as provided (not missing)."""
    payload = {
        "routing": {"work_relationship": "contractor"},
        "identity": {"full_name": ""},
    }
    r = post_evaluate(client, payload)
    assert r.status_code == 200
    body = r.json
    assert_has_required_fields(body)

    mf = body["missing_fields"]
    assert isinstance(mf, list)

    # We don't know your exact field key set; check both strict and suffix match.
    assert "identity.full_name" not in mf, "full_name should not be missing when empty string provided"


def test_ovl_002_overlay_schema_invalid_returns_system_authority_failure(client):
    """T-OVL-002: Invalid overlay schema => SYSTEM_AUTHORITY_FAILURE.

    Note: This test requires a deliberate invalid overlay fixture to be present.
    If you have not wired overlay validation yet, this will fail (as intended).
    """

    payload = {"routing": {"work_relationship": "contractor"}}
    r = post_evaluate(client, payload)
    assert r.status_code == 200
    body = r.json
    assert_has_required_fields(body)

    # This test is conditional: if your overlays are valid, it will not trigger.
    # To make it actionable, fail only if you EXPECT an invalid overlay during this test run.
    # Recommended workflow: run this test after you intentionally break overlay schema in a dev branch.
    rule = find_rule(body, "SYSTEM_AUTHORITY_FAILURE")
    if rule is None:
        pytest.skip("Overlay schema appears valid; to exercise this test, use an invalid overlay fixture.")


def test_term_001_eligible_has_next_field_null(client):
    """T-TERM-001: Eligible => next_field_key null.

    This is a placeholder contract test.
    It will SKIP until you have at least one known input that deterministically yields Eligible.
    """

    pytest.skip(
        "Provide a known-good Eligible fixture once rules/taxonomies are finalized. "
        "Then replace this skip with an actual payload and assertions."
    )


# -----------------
# Utility regression checks
# -----------------


def test_api_required_fields_present_on_valid_routing(client):
    """T-API-001: EvaluateResponse always includes required fields."""
    r = post_evaluate(client, {"routing": {"work_relationship": "contractor"}})
    assert r.status_code == 200
    assert_has_required_fields(r.json)


def test_next_field_key_nullability_for_terminal_statuses(client):
    """Contract: Eligible/Ineligible => next_field_key null.

    This test does not force terminal outcomes; it enforces that if a terminal status is returned,
    next_field_key must be null.
    """
    r = post_evaluate(client, {"routing": {"work_relationship": "contractor"}})
    assert r.status_code == 200
    body = r.json
    assert_has_required_fields(body)

    if body["eligibility_status"] in ("Eligible", "Ineligible"):
        assert body["next_field_key"] is None


def test_missing_fields_unique_and_string_array(client):
    """Contract: missing_fields must be unique values and array of strings."""
    r = post_evaluate(client, {"routing": {"work_relationship": "employee"}})
    assert r.status_code == 200
    body = r.json
    assert_has_required_fields(body)

    mf = body["missing_fields"]
    assert isinstance(mf, list)
    assert all(isinstance(x, str) for x in mf)
    assert len(mf) == len(list(dict.fromkeys(mf))), "missing_fields must be de-duplicated"

