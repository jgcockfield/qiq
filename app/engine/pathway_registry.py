"""Pathway registry for QIQ evaluation flows.

Phase 1 foundation only:
- Costa Rica DNV aliases route to the existing current behavior.
- Spain DNV aliases are registered placeholders for future implementation.
- Costa Rica Pensionado aliases route to the pathway-specific files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


CURRENT_BEHAVIOR = "current"
PLACEHOLDER_BEHAVIOR = "placeholder"
PATHWAY_BEHAVIOR = "pathway"
DEFAULT_PATHWAY_ID = "costa_rica_dnv"


@dataclass(frozen=True)
class PathwayDefinition:
    canonical_id: str
    behavior: str
    implemented: bool
    questions_file: Optional[str] = None
    rules_module: Optional[str] = None
    output_file: Optional[str] = None
    clarifications_file: Optional[str] = None


_PATHWAYS: Dict[str, PathwayDefinition] = {
    "costa-rica-dnv": PathwayDefinition(
        canonical_id="costa_rica_dnv",
        behavior=CURRENT_BEHAVIOR,
        implemented=True,
    ),
    "costa_rica_dnv": PathwayDefinition(
        canonical_id="costa_rica_dnv",
        behavior=CURRENT_BEHAVIOR,
        implemented=True,
    ),
    "spain-dnv": PathwayDefinition(
        canonical_id="spain_dnv",
        behavior=PLACEHOLDER_BEHAVIOR,
        implemented=False,
        questions_file="pathways/spain_dnv/questions.json",
        rules_module="app.engine.pathways.spain_dnv.rules",
    ),
    "spain_dnv": PathwayDefinition(
        canonical_id="spain_dnv",
        behavior=PLACEHOLDER_BEHAVIOR,
        implemented=False,
        questions_file="pathways/spain_dnv/questions.json",
        rules_module="app.engine.pathways.spain_dnv.rules",
    ),
    "costa-rica-pensionado": PathwayDefinition(
        canonical_id="costa_rica_pensionado",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/costa_rica_pensionado/questions.json",
        rules_module="app.engine.pathways.costa_rica_pensionado.rules",
        output_file="pathways/costa_rica_pensionado/output.json",
        clarifications_file="pathways/costa_rica_pensionado/clarifications.json",
    ),
    "costa_rica_pensionado": PathwayDefinition(
        canonical_id="costa_rica_pensionado",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/costa_rica_pensionado/questions.json",
        rules_module="app.engine.pathways.costa_rica_pensionado.rules",
        output_file="pathways/costa_rica_pensionado/output.json",
        clarifications_file="pathways/costa_rica_pensionado/clarifications.json",
    ),
}


def normalize_pathway_id(pathway: Optional[str]) -> str:
    if not pathway:
        return DEFAULT_PATHWAY_ID
    return pathway.strip().lower()


def resolve_pathway(pathway: Optional[str]) -> PathwayDefinition:
    pathway_id = normalize_pathway_id(pathway)
    return _PATHWAYS.get(
        pathway_id,
        PathwayDefinition(
            canonical_id=pathway_id.replace("-", "_"),
            behavior=CURRENT_BEHAVIOR,
            implemented=True,
        ),
    )


def uses_current_behavior(pathway: Optional[str]) -> bool:
    return resolve_pathway(pathway).behavior == CURRENT_BEHAVIOR
