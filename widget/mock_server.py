"""
QIQ Widget — Mock /evaluate server
Run:  uvicorn widget.mock_server:app --port 8001 --reload
Then set data-api-base="http://localhost:8001" in index.html
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import RootModel
from typing import Any, Dict
import pathlib, uuid

app = FastAPI(title="QIQ Mock Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the widget demo page and its assets.
# API routes are defined first so they take precedence over the catch-all mount.
HERE = pathlib.Path(__file__).parent

@app.get("/")
def index():
    return FileResponse(str(HERE / "index.html"))

@app.get("/widget.css")
def serve_css():
    return FileResponse(str(HERE / "widget.css"), media_type="text/css")

@app.get("/widget.js")
def serve_js():
    return FileResponse(str(HERE / "widget.js"), media_type="application/javascript")


# ── Conversation script ───────────────────────────────────────────────────────
# Each step is keyed by the next_field_key we're waiting on.
# "None" (no routing key yet) ->first question.

SCRIPT = [
    {
        "next_field_key": "applicant_type",
        "field": {
            "key":    "applicant_type",
            "prompt": "Are you applying as an employee, self-employed, or business owner?",
            "label":  "Applicant type",
        },
    },
    {
        "next_field_key": "years_experience",
        "field": {
            "key":    "years_experience",
            "prompt": "How many years of relevant professional experience do you have?",
            "label":  "Years of experience",
        },
    },
    {
        "next_field_key": "target_country",
        "field": {
            "key":    "target_country",
            "prompt": "Which country are you applying for?",
            "label":  "Target country",
        },
    },
    {
        "next_field_key": "monthly_income",
        "field": {
            "key":    "monthly_income",
            "prompt": "What is your average gross monthly income (in EUR)?",
            "label":  "Monthly income",
        },
    },
]

def _make_result(status: str, summary: str, flags: list) -> dict:
    """Build a fresh final-result payload with per-call UUIDs."""
    edr_id = str(uuid.uuid4())
    return {
        "next_field_key":    None,
        "field":             None,
        "result": {
            "meta":  {"status": status, "summary": summary},
            "flags": flags,
        },
        "edr_id":            edr_id,
        "edr_path":          f"exports/edr_{edr_id}.json",
        "edr_filename":      f"edr_{edr_id}.json",
        "edr_url":           f"/exports/edr_{edr_id}.json",
        "pdf_url":           f"/reports/edr_{edr_id}.pdf",   # enables PDF button
        "run_id":            str(uuid.uuid4()),
        "export_error":      None,
        "missing_fields":    [],
        "overlay_work_type": None,
        "overlay_version":   None,
    }


class Payload(RootModel[Dict[str, Any]]):
    pass


@app.post("/evaluate")
def mock_evaluate(payload: Payload):
    data    = payload.root or {}
    routing = data.get("routing", {})

    print(f"\n[MOCK] /evaluate hit")
    print(f"  session_id : {data.get('session_id')}")
    print(f"  pathway    : {data.get('pathway')}")
    print(f"  routing    : {routing}")

    # Walk through the script: find the first question whose key is not yet
    # in routing — that's the next question to ask.
    for step in SCRIPT:
        key = step["next_field_key"]
        if key not in routing:
            print(f"  ->next_field_key: {key}")
            return {**step, "missing_fields": [], "overlay_work_type": None, "overlay_version": None}

    # All questions answered — choose result based on income answer
    income_raw = routing.get("monthly_income", "999")
    try:
        income = float("".join(c for c in str(income_raw) if c.isdigit() or c == "."))
    except ValueError:
        income = 0

    if income >= 760:
        result = _make_result(
            "eligible",
            "Based on your answers, you meet the core eligibility requirements for the Portugal D7 Visa.",
            [
                "Monthly income exceeds the minimum threshold (€760/month)",
                "Professional background is compatible with passive-income visa category",
                f"Target country confirmed: {routing.get('target_country', 'Portugal')}",
            ],
        )
    else:
        result = _make_result(
            "not_eligible",
            "Your current income level does not meet the minimum threshold for this visa category.",
            ["Monthly income below minimum threshold (€760/month required)"],
        )

    print(f"  ->FINAL RESULT: {result['result']['meta']['status']} | edr_id: {result['edr_id']}")
    return result
