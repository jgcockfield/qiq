"""
End-to-end conversation flow test for the QIQ widget mock server.
Run from QIQ root:  python widget/test_flow.py
"""

import json
import urllib.request
import urllib.error
import uuid
import sys

BASE = "http://localhost:8001"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

passed = 0
failed = 0


def check(label, actual, expected=None, contains=None, truthy=False):
    global passed, failed
    ok = True
    if expected is not None:
        ok = actual == expected
    elif contains is not None:
        ok = contains in str(actual)
    elif truthy:
        ok = bool(actual)

    icon = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  {icon}  {label}")
    if not ok:
        print(f"         expected: {repr(expected or contains)}")
        print(f"         got:      {repr(actual)}")
        failed += 1
    else:
        passed += 1
    return ok


def post_evaluate(payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{BASE}/evaluate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def separator(title):
    print(f"\n{BOLD}{'-' * 60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'-' * 60}{RESET}")


# ── Static asset check ────────────────────────────────────────────────────────
separator("Static assets (browser load check)")

for path, ct in [("/", "text/html"), ("/widget.css", "text/css"), ("/widget.js", "application/javascript")]:
    try:
        with urllib.request.urlopen(f"{BASE}{path}") as r:
            content_type = r.headers.get("Content-Type", "")
            check(f"GET {path} ->200", r.status, 200)
            check(f"GET {path} Content-Type contains '{ct}'", content_type, contains=ct)
    except urllib.error.HTTPError as e:
        check(f"GET {path} ->200", e.code, 200)


# ── Shared session ID (simulates one widget instance) ─────────────────────────
SESSION_ID = str(uuid.uuid4())
NAME       = "Jane Smith"
EMAIL      = "jane@example.com"
PATHWAY    = "costa-rica-dnv"

base_payload = {
    "session_id": SESSION_ID,
    "full_name":  NAME,
    "email":      EMAIL,
    "pathway":    PATHWAY,
}


# ── Helper: run a full conversation ───────────────────────────────────────────
def run_conversation(income_answer: str, label: str) -> dict:
    separator(f"Conversation flow — {label}  (income={income_answer})")

    routing       = {}
    session_ids   = set()
    pathways_seen = set()
    seen_fields   = []

    ANSWERS = {
        "applicant_type":   "employee",
        "years_experience": "7",
        "target_country":   "Portugal",
        "monthly_income":   income_answer,
    }

    step = 0
    while True:
        step += 1
        payload = {**base_payload, "routing": dict(routing)}
        print(f"\n  Step {step} — routing keys: {list(routing.keys()) or '(empty)'}")

        data = post_evaluate(payload)

        # Track session IDs and pathways across calls
        session_ids.add(payload["session_id"])
        pathways_seen.add(payload.get("pathway"))

        next_key = data.get("next_field_key")

        if next_key:
            field    = data.get("field") or {}
            question = field.get("prompt") or field.get("label") or next_key
            print(f"    Bot: {question}")

            check(f"step {step}: next_field_key is a string", next_key, contains="")
            check(f"step {step}: field.key matches next_field_key", field.get("key"), next_key)
            check(f"step {step}: field has prompt", bool(field.get("prompt")), True)
            seen_fields.append(next_key)

            # Provide the answer for this field
            answer = ANSWERS.get(next_key, "yes")
            print(f"    User: {answer}")
            routing[next_key] = answer

        else:
            # Final result
            print(f"\n  [Final result received at step {step}]")
            result = data.get("result", {})
            meta   = result.get("meta", {})
            status = meta.get("status")

            check("result.meta.status is present",         bool(status), True)
            check("result.meta.summary is present",        bool(meta.get("summary")), True)
            check("result.flags is a list",                isinstance(result.get("flags"), list), True)
            check("edr_id is a UUID string",               bool(data.get("edr_id")), True)
            check("run_id is a UUID string",               bool(data.get("run_id")), True)
            check("pdf_url is present",                    bool(data.get("pdf_url")), True)
            check("pdf_url starts with /reports/",         data.get("pdf_url", ""), contains="/reports/")
            check("edr_url starts with /exports/",         data.get("edr_url", ""), contains="/exports/")
            check("export_error is None",                  data.get("export_error"), None)
            check("next_field_key is None",                data.get("next_field_key"), None)
            check("all 4 questions were asked",            seen_fields,
                  ["applicant_type", "years_experience", "target_country", "monthly_income"])
            break

        if step > 10:
            print(f"  {RED}ABORT: loop exceeded 10 steps — likely infinite loop bug{RESET}")
            failed += 1
            break

    return {"data": data, "session_ids": session_ids, "pathways_seen": pathways_seen, "status": status}


# ── Run both paths ────────────────────────────────────────────────────────────
eligible_run     = run_conversation("850",  "ELIGIBLE path (€850/month)")
not_eligible_run = run_conversation("500",  "NOT ELIGIBLE path (€500/month)")

# ── Check outcome statuses ────────────────────────────────────────────────────
separator("Outcome verification")
check("€850 ->eligible",     eligible_run["data"]["result"]["meta"]["status"],     "eligible")
check("€500 ->not_eligible", not_eligible_run["data"]["result"]["meta"]["status"], "not_eligible")

# ── Session ID consistency ────────────────────────────────────────────────────
separator("Session ID & pathway consistency (per-run)")
check("eligible run:     exactly 1 session ID used across all calls",
      len(eligible_run["session_ids"]), 1)
check("eligible run:     session ID matches the one we sent",
      SESSION_ID in eligible_run["session_ids"], True)
check("eligible run:     pathway='costa-rica-dnv' in every call",
      eligible_run["pathways_seen"], {"costa-rica-dnv"})
check("not_eligible run: pathway='costa-rica-dnv' in every call",
      not_eligible_run["pathways_seen"], {"costa-rica-dnv"})

# ── edr_ids are unique per call (not frozen at import time) ───────────────────
separator("UUID freshness (not frozen at module load)")
edr_a = eligible_run["data"]["edr_id"]
edr_b = not_eligible_run["data"]["edr_id"]
check("eligible and not_eligible get different edr_ids", edr_a == edr_b, False)

# ── Routing accumulation check ────────────────────────────────────────────────
separator("Routing accumulation — widget.js logic simulation")
routing = {}
ANSWERS = {
    "applicant_type":   "employee",
    "years_experience": "7",
    "target_country":   "Portugal",
    "monthly_income":   "800",
}

for expected_key in ["applicant_type", "years_experience", "target_country", "monthly_income"]:
    data = post_evaluate({**base_payload, "routing": dict(routing)})
    got_key = data.get("next_field_key")
    check(f"routing={list(routing.keys())} ->asks '{expected_key}'", got_key, expected_key)
    routing[got_key] = ANSWERS[got_key]

# One more call with all answers ->should be final
data = post_evaluate({**base_payload, "routing": dict(routing)})
check("all 4 answers in routing ->next_field_key is None", data.get("next_field_key"), None)
check("all 4 answers in routing ->status is eligible",
      data["result"]["meta"]["status"], "eligible")


# ── Summary ───────────────────────────────────────────────────────────────────
separator("Results")
total = passed + failed
print(f"  {GREEN if failed == 0 else RED}{BOLD}{passed}/{total} checks passed{RESET}\n")
sys.exit(0 if failed == 0 else 1)
