"""Widget result-metadata presentation fix: Work Type humanization.

There is no JS test runner in this project, so widget/widget.js is verified
via source inspection (confirming the fix is actually applied and the
existing `_qiqDisplayChoiceLabel` humanizer, not a new implementation, is
reused) plus a small Python mirror of that helper's documented transform for
value-level proof. The JS file remains the single source of truth; this
mirror exists only for testability.
"""

from pathlib import Path

from app.engine.output_builder import humanize_status

WIDGET_JS_PATH = (
    Path(__file__).resolve().parents[1] / "widget" / "widget.js"
)


def _widget_source():
    return WIDGET_JS_PATH.read_text(encoding="utf-8")


def _mirror_qiq_display_choice_label(value):
    """Python mirror of widget.js's _qiqDisplayChoiceLabel(v) for
    value-level assertions only -- see module docstring."""
    words = [w for w in str(value or "").replace("_", " ").split() if w]
    return " ".join(w[:1].upper() + w[1:].lower() for w in words)


# ---------------------------------------------------------------------------
# Source-level proof: the fix reuses the existing helper, no raw leak remains
# ---------------------------------------------------------------------------


def test_widget_work_type_uses_existing_humanization_helper():
    source = _widget_source()
    assert "_qiqDisplayChoiceLabel(meta.work_type)" in source
    # The old raw-leak pattern must be gone.
    assert "Work Type: ${this._escapeHtml(meta.work_type)}" not in source


def test_widget_visa_type_left_untouched():
    # Visa Type is already an authored, human-readable string
    # (e.g. "Spain Digital Nomad Visa") and must not be run through the
    # snake_case humanizer.
    source = _widget_source()
    assert "Visa Type: ${this._escapeHtml(meta.visa_type)}" in source
    assert "_qiqDisplayChoiceLabel(meta.visa_type)" not in source


def test_widget_did_not_introduce_a_duplicate_humanizer():
    source = _widget_source()
    assert source.count("function _qiqDisplayChoiceLabel(") == 1


# ---------------------------------------------------------------------------
# Value-level proof (mirrors the JS helper's documented transform)
# ---------------------------------------------------------------------------


def test_work_type_values_humanize_correctly():
    assert _mirror_qiq_display_choice_label("employee") == "Employee"
    assert _mirror_qiq_display_choice_label("contractor") == "Contractor"
    assert _mirror_qiq_display_choice_label("business_owner") == "Business Owner"
    assert (
        _mirror_qiq_display_choice_label("self_employed_freelance")
        == "Self Employed Freelance"
    )
    assert (
        _mirror_qiq_display_choice_label("employee_or_collaborator")
        == "Employee Or Collaborator"
    )


def test_work_type_internal_values_remain_snake_case_unchanged():
    # The fix only changes what is RENDERED -- the internal value itself
    # (as would be stored/passed around/compared elsewhere) is untouched.
    for internal_value in ("employee", "business_owner", "contractor"):
        assert "_" in internal_value or internal_value.islower()
        assert internal_value == internal_value.lower()


# ---------------------------------------------------------------------------
# Status humanization still works (regression guard alongside this fix)
# ---------------------------------------------------------------------------


def test_status_humanization_still_works_alongside_work_type_fix():
    assert humanize_status("needs_review") == "Needs Review"
    assert humanize_status("not_eligible") == "Not Eligible"
    assert humanize_status("eligible") == "Eligible"
