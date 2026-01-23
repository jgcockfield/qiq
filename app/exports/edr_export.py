"""
EDR Export Utilities

Purpose:
- Convert EligibilityDecisionRecord (EDR) into export-ready formats.
- Keep exports deterministic and schema-light for v1.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from app.core.eligibility_decision_record import EligibilityDecisionRecord


def edr_to_sheets_row(edr: EligibilityDecisionRecord) -> Dict[str, Any]:
    """
    Flatten the EDR into a single row suitable for Google Sheets / CRM mapping.
    """
    return edr.to_sheets_row()


def edr_to_json(edr: EligibilityDecisionRecord) -> str:
    """
    Stable JSON export string.
    """
    return edr.to_json()


def write_edr_json(edr: EligibilityDecisionRecord, out_dir: str = "exports") -> str:
    """
    Write EDR to a JSON file and return the filepath.

    Notes:
    - Uses EDR's stable JSON encoding.
    - Filename is based on decision_id (unique) to avoid overwriting.
    """
    os.makedirs(out_dir, exist_ok=True)
    filename = f"edr_{edr.decision_id}.json"
    path = os.path.join(out_dir, filename)

    payload = json.loads(edr_to_json(edr))  # ensure valid JSON
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return path
