"""
Taxonomy Loader

Loads and validates output and clarification taxonomies for QualifyIQ.
This module performs file discovery, JSON parsing, and basic schema checks.
Rendering logic is intentionally excluded.
"""

import json
from pathlib import Path

# taxonomies live at app/taxonomies
TAXONOMY_BASE = Path(__file__).resolve().parent.parent / "taxonomies"

OUTPUT_DIR = TAXONOMY_BASE / "output"
CLARIFICATION_DIR = TAXONOMY_BASE / "clarification"


class TaxonomyLoadError(Exception):
    pass


def _load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise TaxonomyLoadError(f"Failed to load taxonomy file: {path.name}") from e


def load_output_taxonomies() -> dict:
    taxonomies = {}
    for file in OUTPUT_DIR.glob("*.json"):
        data = _load_json(file)

        # Prefer explicit section key; otherwise infer from filename.
        section = data.get("section")
        if not section:
            name = file.stem.lower()
            if "summary" in name:
                section = "summary_statement"
            elif "meta" in name:
                section = "meta"
            elif "cta" in name or "next_steps" in name:
                section = "next_steps"
            else:
                raise TaxonomyLoadError(f"Missing 'section' key in {file.name}")

        taxonomies[section] = data

    # Back-compat: some older taxonomies used 'summary' instead of 'summary_statement'.
    if "summary_statement" not in taxonomies and "summary" in taxonomies:
        taxonomies["summary_statement"] = taxonomies["summary"]

    return taxonomies


def load_clarification_taxonomies() -> dict:
    taxonomies = {}
    for file in CLARIFICATION_DIR.glob("*.json"):
        data = _load_json(file)
        key = data.get("work_type") or data.get("scope")
        if not key:
            raise TaxonomyLoadError(f"Missing work_type or scope in {file.name}")
        taxonomies[key] = data
    return taxonomies


def load_all_taxonomies() -> dict:
    output = load_output_taxonomies()
    clarification = load_clarification_taxonomies()

    # TEMP DEBUG: surface loaded keys explicitly
    print("[taxonomy_loader] output keys:", list(output.keys()))
    print("[taxonomy_loader] clarification keys:", list(clarification.keys()))

    return {
        "output": output,
        "clarification": clarification,
    }


if __name__ == "__main__":
    # Basic smoke test
    all_taxonomies = load_all_taxonomies()
    print("Loaded output taxonomies:", list(all_taxonomies["output"].keys()))
    print("Loaded clarification taxonomies:", list(all_taxonomies["clarification"].keys()))
