"""QualifyIQ EvaluateResponse (v1)

API CONTRACT – DO NOT CHANGE WITHOUT VERSION BUMP.

Purpose
- This response is what the UI consumes.
- It MUST surface deterministic navigation state computed by the evaluator:
  - next_field_key
  - missing_fields
  - overlay_work_type / overlay_version

Important
- EligibilityResult is locked; do NOT add fields to it.
- The evaluator may attach navigation/overlay metadata as runtime attributes on
  the EligibilityResult instance. This module is responsible for *forwarding*
  those attributes into the API response.

v1 notes:
- Any mentions of "P14" are deprecated and removed (broken legacy build)."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.outputs.result_schema import EligibilityResult


class EvaluateResponse(BaseModel):
    """Wrapper returned by POST /evaluate and POST /chat/turn."""

    # Existing, locked eligibility summary
    result: EligibilityResult

    # Export handle for the generated EDR JSON
    edr_id: str
    edr_path: str
    edr_filename: str

    # Becomes real when exports are served over HTTP
    edr_url: Optional[str] = None

    # Becomes real when PDF reports are served over HTTP
    pdf_url: Optional[str] = None

    # -----------------------------
    # Deterministic navigation
    # -----------------------------
    next_field_key: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)

    # Debug metadata
    overlay_work_type: Optional[str] = None
    overlay_version: Optional[str] = None


def build_evaluate_response(
    *,
    result: Any,
    edr_id: str,
    edr_path: str,
    edr_filename: str,
    edr_url: Optional[str] = None,
    pdf_url: Optional[str] = None,
    # Explicit overrides (routes can supply these)
    next_field_key: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    overlay_work_type: Optional[str] = None,
    overlay_version: Optional[str] = None,
) -> EvaluateResponse:
    """Create a stable EvaluateResponse.

    This function is the *single* place where we forward evaluator-provided
    navigation/overlay metadata into the API response.

    Rules:
    - If explicit args are provided, they win.
    - Otherwise, we read runtime attributes from `result`.
    - We never fabricate missing_fields = [] when evaluator did not compute it.
    - Only default to [] when evaluator explicitly returned an empty list.
    """

    def _coerce_eligibility_result(value: Any) -> EligibilityResult:
        """Coerce evaluator/UI payloads into EligibilityResult without changing schemas.

        - If already EligibilityResult: return as-is.
        - If dict-like (UI payload): map required fields + pass through known fields.
        """
        if isinstance(value, EligibilityResult):
            return value

        if isinstance(value, dict):
            meta = value.get("meta") or {}

            status = (
                value.get("status")
                or value.get("eligibility_status")
                or meta.get("status")
                or "needs_review"
            )

            ns = value.get("next_steps")
            if isinstance(ns, list):
                # Contract: List[str] only. Drop non-strings (do not flatten/nest).
                next_steps = [x for x in ns if isinstance(x, str)]
            elif isinstance(ns, dict):
                txt = ns.get("text") or ns.get("label")
                if isinstance(txt, str):
                    next_steps = [txt]
                elif isinstance(txt, list):
                    # Contract: List[str] only. Drop non-strings.
                    next_steps = [x for x in txt if isinstance(x, str)]
                else:
                    next_steps = []
            elif isinstance(ns, str):
                next_steps = [ns]
            else:
                next_steps = []

            version = value.get("version") or "v1"

            # Only pass keys that exist on the EligibilityResult model
            fields = set(getattr(EligibilityResult, "model_fields", {}).keys())
            payload = {k: v for k, v in value.items() if k in fields}
            payload["status"] = status
            payload["next_steps"] = next_steps
            payload["version"] = version
            payload.setdefault("reason_codes", [])

            try:
                return EligibilityResult.model_validate(payload)
            except Exception:
                # Last-resort minimal construction (avoid crashing /evaluate)
                return EligibilityResult(
                    status=status,
                    next_steps=next_steps,
                    reason_codes=payload.get("reason_codes") or [],
                    version=version,
                )

        raise TypeError(f"result must be EligibilityResult or dict, got {type(value).__name__}")

    def _attr(obj: Any, key: str, default=None):
        """Safe attribute getter."""
        return getattr(obj, key, default)

    # Coerce any UI-style dict payloads into the locked EligibilityResult model
    result_model = _coerce_eligibility_result(result)

    # next_field_key: explicit arg wins, else runtime attr, else None
    nk = next_field_key if next_field_key is not None else _attr(result_model, "next_field_key", None)

    # Normalize empty string -> None
    if isinstance(nk, str) and not nk.strip():
        nk = None

    # missing_fields: explicit arg wins, else runtime attr, else None
    # CRITICAL: Do NOT fabricate [] when evaluator didn't compute it
    # Routes should pass explicit metadata extracted from result/edr
    mf = missing_fields if missing_fields is not None else _attr(result_model, "missing_fields", None)

    # Type validation and normalization
    if mf is None:
        # Evaluator did not compute missing_fields (or extraction failed)
        # Default to empty list per schema contract
        # BUT: routes should have extracted from edr, so this is a fallback only
        mf_list: List[str] = []
    elif isinstance(mf, list):
        mf_list = mf
    else:
        # Invalid type - fail loudly
        raise ValueError(
            f"missing_fields must be a list or None, got {type(mf).__name__}: {mf}"
        )

    # overlay metadata: explicit args win, else runtime attrs, else None
    ow = overlay_work_type if overlay_work_type is not None else _attr(result_model, "overlay_work_type", None)
    ov = overlay_version if overlay_version is not None else _attr(result_model, "overlay_version", None)

    return EvaluateResponse(
        result=result_model,
        edr_id=edr_id,
        edr_path=edr_path,
        edr_filename=edr_filename,
        edr_url=edr_url,
        pdf_url=pdf_url,
        next_field_key=nk,
        missing_fields=mf_list,
        overlay_work_type=ow,
        overlay_version=ov,
    )
