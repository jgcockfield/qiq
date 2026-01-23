"""PDF export module (v1)

Deterministic PDF generation from an EligibilityDecisionRecord (EDR).

Design constraints:
- EDR is the ONLY source of truth
- No eligibility logic here
- No browser/headless HTML toolchain
- Keep output stable + simple for demo

Notes:
- If the caller attached a UI result to the EDR (edr.ui_result), we include
  the full UI output section so the PDF matches what the user saw in the UI.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from app.core.eligibility_decision_record import EligibilityDecisionRecord


REPORTS_DIR = Path("exports/reports")


def render_pdf(edr: EligibilityDecisionRecord) -> tuple[str, str]:
    """Render a PDF from an EDR.

    Returns:
        (pdf_filename, pdf_path)
    """

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure hash is present for deterministic export
    if not edr.record_hash:
        edr.compute_hash()

    pdf_filename = f"edr_{edr.decision_id}.pdf"
    pdf_path = REPORTS_DIR / pdf_filename

    c = canvas.Canvas(str(pdf_path), pagesize=LETTER)

    # Header
    y = 760
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Eligibility Decision Record")

    # Body
    y -= 30
    c.setFont("Helvetica", 10)

    lines: list[str] = [
        f"EDR Version: {edr.edr_version}",
        f"Decision ID: {edr.decision_id}",
        f"Created At (UTC): {edr.created_at}",
        f"Program ID: {edr.program_id}",
        f"Program Type: {edr.program_type}",
        "",
        f"Eligibility Status: {edr.eligibility_status}",
        f"Eligible: {edr.eligible}",
    ]

    if edr.primary_reason_code:
        lines.append(f"Primary Reason: {edr.primary_reason_code}")

    if edr.reason_codes:
        lines.append("")
        lines.append("Reason Codes:")
        lines.extend([f" - {rc}" for rc in edr.reason_codes])

    if edr.next_steps:
        lines.append("")
        lines.append("Next Steps:")
        lines.extend([f" - {ns}" for ns in edr.next_steps])

    if edr.missing_fields:
        lines.append("")
        lines.append("Missing Fields:")
        lines.extend([f" - {mf}" for mf in edr.missing_fields])

    # UI Output Section - render the actual user-facing content
    ui_result = getattr(edr, "ui_result", None)

    def _ui_get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    
    def _wrap_text(text: str, max_width: int = 90) -> list[str]:
        """Simple text wrapping for long lines."""
        if len(text) <= max_width:
            return [text]
        words = text.split()
        wrapped_lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_len = len(word) + 1  # +1 for space
            if current_length + word_len > max_width:
                if current_line:
                    wrapped_lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_len
            else:
                current_line.append(word)
                current_length += word_len
        
        if current_line:
            wrapped_lines.append(" ".join(current_line))
        
        return wrapped_lines

    if ui_result:
        lines.append("")
        lines.append("=" * 80)
        lines.append("UI OUTPUT")
        lines.append("=" * 80)
        lines.append("")
        
        # Meta section (status, work_type, visa_type)
        meta = _ui_get(ui_result, "meta", {}) or {}
        status = _ui_get(meta, "status")
        work_type = _ui_get(meta, "work_type")
        visa_type = _ui_get(meta, "visa_type")
        
        if status:
            lines.append(f"Status: {status}")
        if work_type:
            lines.append(f"Work Type: {work_type}")
        if visa_type:
            lines.append(f"Visa Type: {visa_type}")
        
        # Summary
        summary = _ui_get(ui_result, "summary")
        if summary:
            lines.append("")
            lines.append("Summary:")
            for wrapped_line in _wrap_text(summary, 90):
                lines.append(f"  {wrapped_line}")
        
        # Clarifications
        clarifications = _ui_get(ui_result, "clarifications", []) or []
        if clarifications:
            lines.append("")
            lines.append("Clarifications:")
            for i, clarification in enumerate(clarifications, 1):
                if isinstance(clarification, dict):
                    req = clarification.get("requirement", "")
                    title = clarification.get("title", "")
                    clarif_text = clarification.get("clarification", "")
                    
                    lines.append("")
                    lines.append(f"  {i}. {title or req}")
                    if clarif_text:
                        for wrapped_line in _wrap_text(clarif_text, 85):
                            lines.append(f"     {wrapped_line}")
                    
                    # Render nested alternative_evidence sections
                    alt_evidence = clarification.get("alternative_evidence")
                    if alt_evidence and isinstance(alt_evidence, list):
                        lines.append("")
                        lines.append("     Alternative Evidence Options:")
                        for alt in alt_evidence:
                            if isinstance(alt, dict):
                                alt_label = alt.get("label", alt.get("type", ""))
                                alt_desc = alt.get("description", "")
                                
                                lines.append("")
                                lines.append(f"       {alt_label}")
                                if alt_desc:
                                    for wrapped_line in _wrap_text(alt_desc, 75):
                                        lines.append(f"         {wrapped_line}")
                                
                                # Render "Should state:" or "Must include:" etc
                                for key in ["should_state", "must_include", "must_clearly_show"]:
                                    items = alt.get(key)
                                    if items and isinstance(items, list):
                                        key_label = key.replace("_", " ").title() + ":"
                                        lines.append(f"         {key_label}")
                                        for item in items:
                                            if isinstance(item, str):
                                                lines.append(f"           - {item}")
                                
                                # Render requirements/notes
                                for key in ["requirements", "notes"]:
                                    items = alt.get(key)
                                    if items and isinstance(items, list):
                                        key_label = key.title() + ":"
                                        lines.append(f"         {key_label}")
                                        for item in items:
                                            if isinstance(item, str):
                                                for wrapped_line in _wrap_text(item, 70):
                                                    lines.append(f"           - {wrapped_line}")
                    
                    # Render secondary_evidence if present
                    sec_evidence = clarification.get("secondary_evidence")
                    if sec_evidence and isinstance(sec_evidence, list):
                        lines.append("")
                        lines.append("     Secondary Evidence:")
                        for sec in sec_evidence:
                            if isinstance(sec, dict):
                                sec_label = sec.get("label", sec.get("type", ""))
                                sec_desc = sec.get("description", "")
                                
                                lines.append("")
                                lines.append(f"       {sec_label}")
                                if sec_desc:
                                    for wrapped_line in _wrap_text(sec_desc, 75):
                                        lines.append(f"         {wrapped_line}")
        
        # Next Steps
        next_steps_obj = _ui_get(ui_result, "next_steps")
        if next_steps_obj:
            lines.append("")
            lines.append("Next Steps:")
            
            # Check if enabled
            enabled = _ui_get(next_steps_obj, "enabled", True)
            if enabled:
                # Get text array
                text_items = _ui_get(next_steps_obj, "text", [])
                if isinstance(text_items, list):
                    for text_item in text_items:
                        if isinstance(text_item, str):
                            for wrapped_line in _wrap_text(text_item, 85):
                                lines.append(f"  - {wrapped_line}")
                elif isinstance(text_items, str):
                    for wrapped_line in _wrap_text(text_items, 85):
                        lines.append(f"  - {wrapped_line}")
                
                # Get action
                action = _ui_get(next_steps_obj, "action")
                if action and isinstance(action, dict):
                    action_label = _ui_get(action, "label")
                    action_type = _ui_get(action, "type")
                    if action_label:
                        lines.append(f"  Action: {action_label} ({action_type or 'link'})")

    lines.append("")
    lines.append(f"Record Hash: {edr.record_hash}")

    for line in lines:
        c.drawString(40, y, line)
        y -= 14
        if y < 40:
            c.showPage()
            y = 760
            c.setFont("Helvetica", 10)

    c.showPage()
    c.save()

    return pdf_filename, str(pdf_path.resolve())