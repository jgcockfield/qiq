"""EligibilityDecisionRecord (EDR) — v1 executable model

This file turns the canonical contract into a minimal, production-usable record.

Goals for v1:
- Immutable, replayable snapshot of a single eligibility decision
- Contains the exact evaluated inputs, rule trace, and outcome
- Exportable to JSON / Sheets / CRM without re-deriving anything

Non-goals for v1:
- No conversation/session transcript storage
- No advisor notes
- No document readiness scoring

Usage:
- Evaluator builds EligibilityResult and a parallel EligibilityDecisionRecord
- Downstream exports use EDR as the single source of truth
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Phase 12 — identity/session binding (metadata only)
try:
    from app.intake.intake_schema import IdentityMeta
except Exception:  # pragma: no cover
    IdentityMeta = None  # type: ignore


EligibilityStatus = Literal["eligible", "needs_review", "not_eligible"]
ProgramType = Literal["immigration", "grant", "funding", "benefit", "other"]
InputSource = Literal["self_reported", "uploaded_document", "computed", "inferred", "unknown"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json(obj: Any) -> str:
    """Deterministic JSON encoding for hashing."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class EDRRuleTraceItem(BaseModel):
    """Minimal rule-level trace item."""

    rule_id: str
    status: Literal["pass", "needs_review", "fail"]
    reason: Optional[str] = None

    # Explainability / provenance
    description: Optional[str] = None
    source_url: Optional[str] = None
    source_authority: Optional[str] = None
    source_excerpt: Optional[str] = None


class EligibilityDecisionRecord(BaseModel):
    """Immutable eligibility decision artifact."""

    # Identity & metadata
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Phase 12: identity/session binding (stored as metadata; NOT used in eligibility logic)
    identity: Optional[Any] = Field(
        None,
        description="Identity metadata (name/email/session_id/client_reference_id). Not used in eligibility logic.",
    )
    program_id: str = "CR_DN"
    program_type: ProgramType = "immigration"

    # Versioning
    edr_version: str = "1.0"         # EDR schema version
    rule_version: str = "v1"          # ruleset identifier applied
    engine_version: str = "v1"        # engine build/version

    # Timestamp
    created_at: str = Field(default_factory=_utc_now_iso)

    # Input snapshot (frozen)
    raw_inputs: Dict[str, Any] = Field(default_factory=dict)
    derived_inputs: Dict[str, Any] = Field(default_factory=dict)
    input_sources: Dict[str, InputSource] = Field(default_factory=dict)

    # Outcome
    eligibility_status: EligibilityStatus
    eligible: bool
    reason_codes: List[str] = Field(default_factory=list)
    primary_reason_code: Optional[str] = None
    next_steps: List[str] = Field(default_factory=list)

    # Phase 14: deterministic navigation + overlay metadata (persisted)
    missing_fields: List[str] = Field(default_factory=list)
    next_field_key: Optional[str] = None
    overlay_work_type: Optional[str] = None
    overlay_version: Optional[str] = None

    # Explanation buckets
    risk_buckets: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)

    # Rule trace (critical)
    rule_results: List[EDRRuleTraceItem] = Field(default_factory=list)

    # Integrity
    record_hash: str = ""
    immutable_flag: bool = True

    def compute_hash(self) -> str:
        """Compute and set record_hash based on deterministic serialization.

        IMPORTANT (v1): exclude decision_id + created_at so the hash is stable
        for identical inputs/outcomes across runs.
        """
        payload = self.model_dump(
            exclude={"record_hash", "decision_id", "created_at"},
            mode="python",
        )
        h = _sha256_hex(_stable_json(payload))
        object.__setattr__(self, "record_hash", h)
        return h

    def to_json(self) -> str:
        """Stable JSON export for downstream systems."""
        if not self.record_hash:
            self.compute_hash()
        return _stable_json(self.model_dump(mode="python"))

    def to_dict(self) -> Dict[str, Any]:
        if not self.record_hash:
            self.compute_hash()
        return self.model_dump(mode="python")

    def to_sheets_row(self) -> Dict[str, Any]:
        """Flattened row for Google Sheets / CRM mapping."""
        if not self.record_hash:
            self.compute_hash()

        return {
            "decision_id": self.decision_id,
            # Phase 12: flattened identity (optional)
            "session_id": (self.identity.get("session_id") if isinstance(self.identity, dict) else getattr(self.identity, "session_id", None)) if self.identity else None,
            "name": (self.identity.get("name") if isinstance(self.identity, dict) else getattr(self.identity, "name", None)) if self.identity else None,
            "email": (self.identity.get("email") if isinstance(self.identity, dict) else getattr(self.identity, "email", None)) if self.identity else None,
            "client_reference_id": (self.identity.get("client_reference_id") if isinstance(self.identity, dict) else getattr(self.identity, "client_reference_id", None)) if self.identity else None,
            "program_id": self.program_id,
            "program_type": self.program_type,
            "rule_version": self.rule_version,
            "engine_version": self.engine_version,
            "created_at": self.created_at,
            "eligibility_status": self.eligibility_status,
            "eligible": self.eligible,
            "primary_reason_code": self.primary_reason_code,
            "reason_codes": "|".join(self.reason_codes),
            "next_steps": " | ".join(self.next_steps),
            "next_field_key": self.next_field_key,
            "missing_fields": "|".join(self.missing_fields) if self.missing_fields else "",
            "overlay_work_type": self.overlay_work_type,
            "overlay_version": self.overlay_version,
            "record_hash": self.record_hash,
        }


# ---------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------


def build_edr_from_evaluator(
    *,
    request_like: Any,
    eligibility_result_like: Any,
    rule_results_like: List[Any],
    identity_like: Optional[Any] = None,
    risk_buckets: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    program_id: str = "CR_DN",
    program_type: ProgramType = "immigration",
    rule_version: str = "v1",
    engine_version: str = "v1",
) -> EligibilityDecisionRecord:
    """Construct an EDR from the current evaluator surfaces."""

    def _get(obj: Any, key: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    raw_inputs: Dict[str, Any] = {}
    for k in (
        "visa_type",
        "destination_country",
        "monthly_income_usd",
        "passport_expiry_date",
        "passport_expiration_date",
        "has_health_insurance",
        "applicant_type",
        "work_relationship",
    ):
        v = _get(request_like, k, None)
        if v is not None:
            raw_inputs[k] = v

    eligibility_status = _get(
        eligibility_result_like, 
        "eligibility_status",
        _get(eligibility_result_like, "status", _get(eligibility_result_like, "final_status"))
    )
    eligible = bool(_get(eligibility_result_like, "eligible", eligibility_status == "eligible"))
    reason_codes = list(_get(eligibility_result_like, "reason_codes", []))
    primary_reason_code = _get(eligibility_result_like, "primary_reason_code", None)
    next_steps = list(_get(eligibility_result_like, "next_steps", []))

    # Phase 14: navigation + overlay metadata
    missing_fields = list(_get(eligibility_result_like, "missing_fields", []))
    next_field_key = _get(eligibility_result_like, "next_field_key", None)
    overlay_work_type = _get(eligibility_result_like, "overlay_work_type", None)
    overlay_version = _get(eligibility_result_like, "overlay_version", None)

    edr_rule_results: List[EDRRuleTraceItem] = []
    for rr in rule_results_like or []:
        edr_rule_results.append(
            EDRRuleTraceItem(
                rule_id=_get(rr, "rule_id"),
                status=_get(rr, "status"),
                reason=_get(rr, "reason", None),
                description=_get(rr, "description", None),
                source_url=_get(rr, "source_url", None),
                source_authority=_get(rr, "source_authority", None),
                source_excerpt=_get(rr, "source_excerpt", None),
            )
        )

    edr = EligibilityDecisionRecord(
        program_id=program_id,
        identity=(identity_like.model_dump() if hasattr(identity_like, "model_dump") else identity_like),
        program_type=program_type,
        rule_version=rule_version,
        engine_version=engine_version,
        raw_inputs=raw_inputs,
        eligibility_status=eligibility_status,
        eligible=eligible,
        reason_codes=reason_codes,
        primary_reason_code=primary_reason_code,
        next_steps=next_steps,
        risk_buckets=risk_buckets or {},
        rule_results=edr_rule_results,
        missing_fields=missing_fields,
        next_field_key=next_field_key,
        overlay_work_type=overlay_work_type,
        overlay_version=overlay_version,
    )

    edr.compute_hash()
    return edr