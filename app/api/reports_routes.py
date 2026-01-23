from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

REPORTS_DIR = Path("exports/reports")


@router.get("/reports/{filename}")
def download_report(filename: str):
    # basic safety: only our generated filenames
    if not filename.startswith("edr_") or not filename.endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Not found")

    path = (REPORTS_DIR / filename).resolve()

    # prevent path traversal
    if REPORTS_DIR.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail="Not found")

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    return FileResponse(str(path), media_type="application/pdf", filename=filename)
