from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()

EXPORTS_DIR = "exports"


@router.get("/exports/{filename}")
def download_export(filename: str):
    # Basic validation
    if not filename.startswith("edr_") or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid export filename")

    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    path = os.path.join(EXPORTS_DIR, filename)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        media_type="application/json",
        filename=filename,
    )
