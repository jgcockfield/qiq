from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, PrivateAttr, ConfigDict



class DocumentReadiness(BaseModel):
    """Deterministic readiness scoring (P2 S6)."""

    score: int = Field(..., ge=0, le=100, description="0–100 readiness score")
    level: Literal["high", "medium", "low"] = Field(..., description="high | medium | low")
    gaps: List[str] = Field(default_factory=list, description="What is missing / weak")


class EligibilityResult(BaseModel):
    """Canonical eligibility result returned by QualifyIQ.

    This is a structured output contract (API surface), not business logic.

    Phase 2 changes:
    - `status` is now one of: eligible | needs_review | not_eligible
    - `reason_codes` is the canonical explainability payload (deterministic)
    - `primary_reason_code` is the first / most severe reason (or None)
    - `document_readiness` provides numeric evidence readiness scoring

    Back-compat:
    - `reasons` and `risk_flags` are retained but deprecated.
    
    Phase 14 runtime attributes:
    - Evaluator attaches overlay/navigation metadata via object.__setattr__
    - Pydantic v2 extra='allow' permits this
    """

    # CRITICAL: Allow runtime attributes from evaluator
    model_config = ConfigDict(extra="allow")

    # Core decision
    eligible: Optional[bool] = Field(None, description="Boolean convenience flag")
    status: Literal["eligible", "needs_review", "not_eligible"] = Field(
        ..., description="eligible | needs_review | not_eligible"
    )

    # Phase 2 explainability
    reason_codes: List[str] = Field(default_factory=list, description="Deterministic reason codes")
    primary_reason_code: Optional[str] = Field(None, description="First reason code (most severe), if any")

    # Phase 2 readiness scoring
    document_readiness: Optional[DocumentReadiness] = Field(
        None, description="0–100 readiness score + gaps"
    )

    # Backward-compatible fields (deprecated)
    reasons: List[str] = Field(
        default_factory=list,
        description="DEPRECATED: use reason_codes instead",
    )
    risk_flags: List[str] = Field(
        default_factory=list,
        description="DEPRECATED: use reason_codes + document_readiness.gaps instead",
    )

    # Guidance
    next_steps: List[str] = Field(
        default_factory=list, description="Recommended next actions"
    )

    # Phase 3: Readiness summary + grouped risk buckets
    readiness_state: Optional[Literal["not_eligible", "needs_review", "eligible"]] = Field(
        None,
        description="Optional summary state (aligned to status)"
    )

    risk_buckets: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None,
        description="P3 S2 grouped non-pass rules for user-facing summaries",
    )

    # Metadata
    version: str = Field("v1", description="API schema version")
