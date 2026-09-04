"""Pathway registry for QIQ evaluation flows.

Phase 1 foundation only:
- Costa Rica DNV aliases route to the existing current behavior.
- Spain DNV aliases are registered placeholders for future implementation.
- Costa Rica Pensionado aliases route to the pathway-specific files.
- Spain Non-Lucrative Visa aliases route to the pathway-specific files.
- Spain Student Visa aliases route to the pathway-specific files.
- Italy Digital Nomad Visa aliases route to the pathway-specific files.
- Italy Elective Residence Visa aliases route to the pathway-specific files.
- Portugal D7 Passive Income Visa aliases route to the pathway-specific files.
- Portugal Digital Nomad Visa aliases route to the pathway-specific files.
- Portugal Golden Visa / ARI aliases route to the pathway-specific files.
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
    "spain-nlv": PathwayDefinition(
        canonical_id="spain_nlv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/spain_nlv/questions.json",
        rules_module="app.engine.pathways.spain_nlv.rules",
        output_file="pathways/spain_nlv/output.json",
        clarifications_file="pathways/spain_nlv/clarifications.json",
    ),
    "spain_nlv": PathwayDefinition(
        canonical_id="spain_nlv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/spain_nlv/questions.json",
        rules_module="app.engine.pathways.spain_nlv.rules",
        output_file="pathways/spain_nlv/output.json",
        clarifications_file="pathways/spain_nlv/clarifications.json",
    ),
    "spain-student-visa": PathwayDefinition(
        canonical_id="spain_student_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/spain_student_visa/questions.json",
        rules_module="app.engine.pathways.spain_student_visa.rules",
        output_file="pathways/spain_student_visa/output.json",
        clarifications_file="pathways/spain_student_visa/clarifications.json",
    ),
    "spain_student_visa": PathwayDefinition(
        canonical_id="spain_student_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/spain_student_visa/questions.json",
        rules_module="app.engine.pathways.spain_student_visa.rules",
        output_file="pathways/spain_student_visa/output.json",
        clarifications_file="pathways/spain_student_visa/clarifications.json",
    ),
    "italy_dnv": PathwayDefinition(
        canonical_id="italy_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/italy_dnv/questions.json",
        rules_module="app.engine.pathways.italy_dnv.rules",
        output_file="pathways/italy_dnv/output.json",
        clarifications_file="pathways/italy_dnv/clarifications.json",
    ),
    "italy-dnv": PathwayDefinition(
        canonical_id="italy_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/italy_dnv/questions.json",
        rules_module="app.engine.pathways.italy_dnv.rules",
        output_file="pathways/italy_dnv/output.json",
        clarifications_file="pathways/italy_dnv/clarifications.json",
    ),
    "italy-digital-nomad": PathwayDefinition(
        canonical_id="italy_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/italy_dnv/questions.json",
        rules_module="app.engine.pathways.italy_dnv.rules",
        output_file="pathways/italy_dnv/output.json",
        clarifications_file="pathways/italy_dnv/clarifications.json",
    ),
    "italy-digital-nomad-visa": PathwayDefinition(
        canonical_id="italy_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/italy_dnv/questions.json",
        rules_module="app.engine.pathways.italy_dnv.rules",
        output_file="pathways/italy_dnv/output.json",
        clarifications_file="pathways/italy_dnv/clarifications.json",
    ),
    "italy-elective-residence": PathwayDefinition(
        canonical_id="italy_elective_residence",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/italy_elective_residence/questions.json",
        rules_module="app.engine.pathways.italy_elective_residence.rules",
        output_file="pathways/italy_elective_residence/output.json",
        clarifications_file="pathways/italy_elective_residence/clarifications.json",
    ),
    "italy_elective_residence": PathwayDefinition(
        canonical_id="italy_elective_residence",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/italy_elective_residence/questions.json",
        rules_module="app.engine.pathways.italy_elective_residence.rules",
        output_file="pathways/italy_elective_residence/output.json",
        clarifications_file="pathways/italy_elective_residence/clarifications.json",
    ),
    "portugal-d7": PathwayDefinition(
        canonical_id="portugal_d7",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_d7/questions.json",
        rules_module="app.engine.pathways.portugal_d7.rules",
        output_file="pathways/portugal_d7/output.json",
        clarifications_file="pathways/portugal_d7/clarifications.json",
    ),
    "portugal_d7": PathwayDefinition(
        canonical_id="portugal_d7",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_d7/questions.json",
        rules_module="app.engine.pathways.portugal_d7.rules",
        output_file="pathways/portugal_d7/output.json",
        clarifications_file="pathways/portugal_d7/clarifications.json",
    ),
    "portugal-dnv": PathwayDefinition(
        canonical_id="portugal_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_dnv/questions.json",
        rules_module="app.engine.pathways.portugal_dnv.rules",
        output_file="pathways/portugal_dnv/output.json",
        clarifications_file="pathways/portugal_dnv/clarifications.json",
    ),
    "portugal_dnv": PathwayDefinition(
        canonical_id="portugal_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_dnv/questions.json",
        rules_module="app.engine.pathways.portugal_dnv.rules",
        output_file="pathways/portugal_dnv/output.json",
        clarifications_file="pathways/portugal_dnv/clarifications.json",
    ),
    "portugal-digital-nomad": PathwayDefinition(
        canonical_id="portugal_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_dnv/questions.json",
        rules_module="app.engine.pathways.portugal_dnv.rules",
        output_file="pathways/portugal_dnv/output.json",
        clarifications_file="pathways/portugal_dnv/clarifications.json",
    ),
    "portugal-digital-nomad-visa": PathwayDefinition(
        canonical_id="portugal_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_dnv/questions.json",
        rules_module="app.engine.pathways.portugal_dnv.rules",
        output_file="pathways/portugal_dnv/output.json",
        clarifications_file="pathways/portugal_dnv/clarifications.json",
    ),
    "portugal-remote-work": PathwayDefinition(
        canonical_id="portugal_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_dnv/questions.json",
        rules_module="app.engine.pathways.portugal_dnv.rules",
        output_file="pathways/portugal_dnv/output.json",
        clarifications_file="pathways/portugal_dnv/clarifications.json",
    ),
    "portugal-remote-work-visa": PathwayDefinition(
        canonical_id="portugal_dnv",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_dnv/questions.json",
        rules_module="app.engine.pathways.portugal_dnv.rules",
        output_file="pathways/portugal_dnv/output.json",
        clarifications_file="pathways/portugal_dnv/clarifications.json",
    ),
    "portugal-golden-visa": PathwayDefinition(
        canonical_id="portugal_golden_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_golden_visa/questions.json",
        rules_module="app.engine.pathways.portugal_golden_visa.rules",
        output_file="pathways/portugal_golden_visa/output.json",
        clarifications_file="pathways/portugal_golden_visa/clarifications.json",
    ),
    "portugal_golden_visa": PathwayDefinition(
        canonical_id="portugal_golden_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_golden_visa/questions.json",
        rules_module="app.engine.pathways.portugal_golden_visa.rules",
        output_file="pathways/portugal_golden_visa/output.json",
        clarifications_file="pathways/portugal_golden_visa/clarifications.json",
    ),
    "portugal-ari": PathwayDefinition(
        canonical_id="portugal_golden_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_golden_visa/questions.json",
        rules_module="app.engine.pathways.portugal_golden_visa.rules",
        output_file="pathways/portugal_golden_visa/output.json",
        clarifications_file="pathways/portugal_golden_visa/clarifications.json",
    ),
    "portugal_ari": PathwayDefinition(
        canonical_id="portugal_golden_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_golden_visa/questions.json",
        rules_module="app.engine.pathways.portugal_golden_visa.rules",
        output_file="pathways/portugal_golden_visa/output.json",
        clarifications_file="pathways/portugal_golden_visa/clarifications.json",
    ),
    "portugal-investment-residence": PathwayDefinition(
        canonical_id="portugal_golden_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_golden_visa/questions.json",
        rules_module="app.engine.pathways.portugal_golden_visa.rules",
        output_file="pathways/portugal_golden_visa/output.json",
        clarifications_file="pathways/portugal_golden_visa/clarifications.json",
    ),
    "portugal-investment-residence-permit": PathwayDefinition(
        canonical_id="portugal_golden_visa",
        behavior=PATHWAY_BEHAVIOR,
        implemented=True,
        questions_file="pathways/portugal_golden_visa/questions.json",
        rules_module="app.engine.pathways.portugal_golden_visa.rules",
        output_file="pathways/portugal_golden_visa/output.json",
        clarifications_file="pathways/portugal_golden_visa/clarifications.json",
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
