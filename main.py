# API BOUNDARY ADAPTER
# Do not implement eligibility logic here.
# This file delegates to the evaluator engine.

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.engine.evaluator import evaluate as engine_evaluate

app = FastAPI()

VALID_WORK = {"employee", "contractor", "business_owner"}


def authority_failure(reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "eligibility_status": "Needs Review",
            "rule_results": [
                {
                    "rule_id": "SYSTEM_AUTHORITY_FAILURE",
                    "status": "needs_review",
                    "reason": reason,
                }
            ],
            "missing_fields": [],
            "next_field_key": None,
            "disclaimer_text": "stub",
        },
    )


@app.post("/evaluate")
def evaluate(payload: Dict[str, Any]):
    routing = payload.get("routing")
    if not isinstance(routing, dict):
        return authority_failure("Missing routing object")

    work = routing.get("work_relationship")
    if work not in VALID_WORK:
        return authority_failure("Invalid work_relationship")

    # Normalize identity from Gravity Forms gate (name/email submitted before QIQ)
    identity = payload.get("identity", {})
    if not isinstance(identity, dict):
        identity = {}

    # Gravity Forms field IDs: name, email
    if "name" in payload and "full_name" not in identity:
        identity["full_name"] = payload["name"]

    if "email" in payload and "email" not in identity:
        identity["email"] = payload["email"]

    payload["identity"] = identity

    # Delegate to evaluator engine (logic lives there)
    try:
        result = engine_evaluate(payload)
    except NotImplementedError:
        # Temporary stub until engine is implemented
        result = {
            "eligibility_status": "Needs Review",
            "rule_results": [],
            "missing_fields": [],
            "next_field_key": None,
            "disclaimer_text": "stub",
        }

    return JSONResponse(status_code=200, content=result)
