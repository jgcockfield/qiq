"""Admin Console API Routes

Read-only endpoints for viewing exported EDRs and completed runs.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

from app.storage.run_store import list_runs

router = APIRouter(prefix="/admin/api", tags=["admin"])

EXPORTS_DIR = Path("exports")


def _is_safe_edr_id(edr_id: str) -> bool:
    """Validate that edr_id looks like a UUID (basic safety check)."""
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, edr_id.lower()))


@router.get("/edr")
async def list_edrs() -> List[Dict[str, Any]]:
    """List all EDR exports (most recent first)."""

    if not EXPORTS_DIR.exists():
        return []

    edrs = []

    for filepath in EXPORTS_DIR.glob("edr_*.json"):
        try:
            filename = filepath.name
            edr_id = filename.replace("edr_", "").replace(".json", "")
            mtime = filepath.stat().st_mtime

            status = None
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    status = data.get("eligibility_status")
            except Exception:
                pass

            edrs.append({
                "edr_id": edr_id,
                "filename": filename,
                "created_at": mtime,
                "status": status,
            })

        except Exception:
            continue

    edrs.sort(key=lambda x: x["created_at"], reverse=True)
    return edrs


@router.get("/edr/{edr_id}")
async def get_edr(edr_id: str) -> Dict[str, Any]:
    """Get full EDR JSON by ID."""

    if not _is_safe_edr_id(edr_id):
        raise HTTPException(status_code=400, detail=f"Invalid edr_id format: {edr_id}")

    filename = f"edr_{edr_id}.json"
    filepath = EXPORTS_DIR / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"EDR not found: {edr_id}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading EDR: {e}")


@router.get("/runs")
def list_runs_api():
    """List completed eligibility runs (records table source)."""
    return list_runs()
