from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import RootModel

from app.api.exports_routes import router as exports_router
from app.api.reports_routes import router as reports_router
from app.api.admin_routes import router as admin_router
from app.core.eligibility_decision_record import build_edr_from_evaluator
from app.engine.evaluator import evaluate
from app.engine.eligibility_rules import evaluate_eligibility
from app.exports.edr_export import write_edr_json
from app.exports.pdf_export import render_pdf
from app.engine.output_builder import build_output

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(exports_router)
app.include_router(reports_router)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# Mount admin static files
app.mount("/admin", StaticFiles(directory="app/admin/static", html=True), name="admin")


class EvaluatePayload(RootModel[Dict[str, Any]]):
    """Accept arbitrary intake payloads during Build 2."""

    pass


def _nav_response(res: Dict[str, Any]) -> Dict[str, Any]:
    """Navigation-only response (no eligibility, no exports)."""

    return {
        "result": None,
        "edr_id": None,
        "edr_path": None,
        "edr_filename": None,
        "edr_url": None,
        "pdf_url": None,
        "next_field_key": res.get("next_field_key"),
        "missing_fields": res.get("missing_fields", []),
        "field": res.get("field"),
        "overlay_work_type": res.get("overlay_work_type"),
        "overlay_version": res.get("overlay_version"),
    }


@app.post("/evaluate")
async def run_evaluate(payload: EvaluatePayload = Body(default={})):  # noqa: B008
    data = payload.root or {}

    # 1) Deterministic evaluator (next question OR completion)
    res = evaluate(data)

    # 2) Navigation phase
    if res.get("next_field_key") is not None:
        logger.debug(f"Navigation phase: next_field_key={res.get('next_field_key')}")
        return _nav_response(res)

    # 3) Final eligibility phase
    print("=" * 80)
    print("DEBUG: ENTERING FINAL ELIGIBILITY PHASE")
    print("=" * 80)
    logger.info("Entering final eligibility phase")
    eligibility_raw = evaluate_eligibility(data) or {}

    # 4) Build UI output (this is what we want in the PDF)
    ui_result = build_output(
        {
            **eligibility_raw,
            "routing": eligibility_raw.get("routing") or data.get("routing", {}),
        }
    )
    
    print(f"DEBUG: ui_result type: {type(ui_result)}")
    print(f"DEBUG: ui_result keys: {ui_result.keys() if isinstance(ui_result, dict) else 'NOT A DICT'}")
    if isinstance(ui_result, dict) and 'meta' in ui_result:
        print(f"DEBUG: ui_result.meta.status = {ui_result.get('meta', {}).get('status')}")
    print(f"DEBUG: eligibility_raw.eligibility_status BEFORE fix = {eligibility_raw.get('eligibility_status')}")
    
    # FIX: Map ui_result.meta.status back to eligibility_raw for EDR validation
    # This prevents "eligibility_status must be 'eligible', 'needs_review', or 'not_eligible'" error
    if eligibility_raw.get("eligibility_status") is None and ui_result:
        meta_status = ui_result.get("meta", {}).get("status")
        if meta_status:
            logger.info(f"Mapping ui_result.meta.status='{meta_status}' to eligibility_raw.eligibility_status")
            eligibility_raw["eligibility_status"] = meta_status
        else:
            logger.warning("No status in ui_result.meta, defaulting eligibility_status='needs_review'")
            eligibility_raw["eligibility_status"] = "needs_review"
    
    print(f"DEBUG: eligibility_raw.eligibility_status AFTER fix = {eligibility_raw.get('eligibility_status')}")
    print("=" * 80)
    
    # 5) Build + persist EDR + PDF
    edr = None
    edr_path = None
    edr_filename = None
    edr_url = None
    pdf_url = None
    export_error = None

    # 5a) Build + persist EDR with comprehensive error handling
    try:
        logger.info("Building EDR from evaluator...")
        
        edr = build_edr_from_evaluator(
            request_like=data,
            eligibility_result_like=eligibility_raw,
            rule_results_like=[],
        )

        # Attach UI output BEFORE PDF render
        object.__setattr__(edr, "ui_result", ui_result)

        logger.info("Writing EDR to JSON...")
        edr_path = write_edr_json(edr)
        edr_filename = os.path.basename(edr_path)
        edr_url = f"/exports/{edr_filename}"
        logger.info(f"✓ EDR created successfully: {edr_filename}")
        
    except ImportError as e:
        error_msg = f"EDR module import failed: {e}"
        logger.error(error_msg, exc_info=True)
        export_error = error_msg
    except FileNotFoundError as e:
        error_msg = f"EDR file/directory not found: {e}"
        logger.error(error_msg, exc_info=True)
        export_error = error_msg
    except PermissionError as e:
        error_msg = f"EDR permission denied: {e}"
        logger.error(error_msg, exc_info=True)
        export_error = error_msg
    except Exception as e:
        error_msg = f"EDR export failed: {e}"
        logger.error(error_msg, exc_info=True)
        export_error = error_msg

    # 5b) Generate PDF only if EDR exists - with comprehensive error handling
    if edr is not None:
        try:
            logger.info(f"Generating PDF for EDR: {edr.decision_id if hasattr(edr, 'decision_id') else 'unknown'}...")
            pdf_filename, _pdf_path = render_pdf(edr)
            pdf_url = f"/reports/{pdf_filename}"
            logger.info(f"✓ PDF generated successfully: {pdf_filename}")
            
        except ImportError as e:
            error_msg = f"PDF library missing (install required dependencies): {e}"
            logger.error(error_msg, exc_info=True)
            export_error = error_msg if export_error is None else f"{export_error}; {error_msg}"
        except FileNotFoundError as e:
            error_msg = f"PDF template/resource not found: {e}"
            logger.error(error_msg, exc_info=True)
            export_error = error_msg if export_error is None else f"{export_error}; {error_msg}"
        except PermissionError as e:
            error_msg = f"PDF write permission denied: {e}"
            logger.error(error_msg, exc_info=True)
            export_error = error_msg if export_error is None else f"{export_error}; {error_msg}"
        except AttributeError as e:
            error_msg = f"PDF render failed - missing EDR attribute: {e}"
            logger.error(error_msg, exc_info=True)
            export_error = error_msg if export_error is None else f"{export_error}; {error_msg}"
        except Exception as e:
            error_msg = f"PDF export failed: {e}"
            logger.error(error_msg, exc_info=True)
            export_error = error_msg if export_error is None else f"{export_error}; {error_msg}"
    else:
        logger.warning("⚠ Skipping PDF generation - EDR is None")
        if export_error is None:
            export_error = "PDF generation skipped - EDR creation failed"

    # Log final status
    if export_error:
        logger.error(f"Export completed with errors: {export_error}")
    else:
        logger.info("✓ Export completed successfully")

    return {
        "result": ui_result,
        "edr_id": (edr.decision_id if edr else None),
        "edr_path": edr_path,
        "edr_filename": edr_filename,
        "edr_url": edr_url,
        "pdf_url": pdf_url,
        "export_error": export_error,
        "next_field_key": None,
        "missing_fields": [],
        "field": None,
        "overlay_work_type": None,
        "overlay_version": None,
    }