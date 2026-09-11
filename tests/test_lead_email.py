"""Presentation cleanup for app/notifications/lead_email.py.

Scope: this notification's visible subject/body content only. Internal
values, email routing (the DEMO-mode "send to the prospect's own inbox"
behavior), and sendgrid invocation are explicitly NOT covered by this cleanup
and must remain unchanged -- see test_lead_email_routing_unchanged below.
"""

from unittest.mock import MagicMock, patch

from app.notifications.lead_email import (
    _build_subject_and_body,
    _send,
    send_lead_notification,
)


def _sample_kwargs(status):
    return dict(
        full_name="Jane Applicant",
        email="jane@example.com",
        phone="+1-555-0100",
        pathway="italy_elective_residence",
        status=status,
        created_at="2026-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Items 1-2: raw internal status values never visibly rendered
# ---------------------------------------------------------------------------


def test_lead_email_never_visibly_renders_needs_review():
    subject, body = _build_subject_and_body(**_sample_kwargs("needs_review"))
    assert "needs_review" not in subject
    assert "needs_review" not in body


def test_lead_email_never_visibly_renders_not_eligible():
    subject, body = _build_subject_and_body(**_sample_kwargs("not_eligible"))
    assert "not_eligible" not in subject
    assert "not_eligible" not in body


# ---------------------------------------------------------------------------
# Items 3-5: humanized display for each of the three internal statuses
# ---------------------------------------------------------------------------


def test_lead_email_eligible_displays_correctly():
    subject, body = _build_subject_and_body(**_sample_kwargs("eligible"))
    assert "Eligible" in subject
    assert "Status:   Eligible" in body
    assert "eligible" not in subject  # no raw/lowercase leak alongside it
    assert "not eligible" not in subject.lower()


def test_lead_email_needs_review_displays_correctly():
    subject, body = _build_subject_and_body(**_sample_kwargs("needs_review"))
    assert "Needs Review" in subject
    assert "Status:   Needs Review" in body


def test_lead_email_not_eligible_displays_correctly():
    subject, body = _build_subject_and_body(**_sample_kwargs("not_eligible"))
    assert "Not Eligible" in subject
    assert "Status:   Not Eligible" in body


def test_lead_email_unknown_or_missing_status_is_safe():
    subject, body = _build_subject_and_body(**_sample_kwargs(None))
    assert "Unknown" in subject
    assert "_" not in subject
    assert "None" not in subject


# ---------------------------------------------------------------------------
# Item 6: raw requirement/reason codes -- this notification does not
# currently render any (no failed_requirements/reason_codes parameter
# exists on send_lead_notification / _build_subject_and_body at all).
# Guard against a future regression that adds one without humanizing it.
# ---------------------------------------------------------------------------


def test_lead_email_carries_no_requirement_or_reason_code_parameter():
    import inspect

    sig = inspect.signature(_build_subject_and_body)
    assert "failed_requirements" not in sig.parameters
    assert "reason_codes" not in sig.parameters

    send_sig = inspect.signature(send_lead_notification)
    assert "failed_requirements" not in send_sig.parameters
    assert "reason_codes" not in send_sig.parameters


def test_lead_email_body_contains_no_snake_case_requirement_style_codes():
    # A representative sample of real requirement codes must never appear in
    # the rendered body even if a caller mistakenly passed one in as status.
    for fake_code in ("income_below_minimum", "passport_validity_below_minimum"):
        subject, body = _build_subject_and_body(**_sample_kwargs(fake_code))
        # humanize_status falls back to mechanical Title Case for any
        # unrecognized snake_case value, so the raw code must not survive.
        assert fake_code not in subject
        assert fake_code not in body


# ---------------------------------------------------------------------------
# Item 7: internal values passed INTO the notification remain snake_case
# ---------------------------------------------------------------------------


def test_internal_status_value_passed_in_remains_snake_case():
    # The function accepts and threads through the raw snake_case value --
    # only what is RENDERED is humanized, never the internal contract.
    kwargs = _sample_kwargs("needs_review")
    assert kwargs["status"] == "needs_review"
    # _build_subject_and_body does not mutate or return the internal value.
    result = _build_subject_and_body(**kwargs)
    assert kwargs["status"] == "needs_review"
    assert isinstance(result, tuple) and len(result) == 2


# ---------------------------------------------------------------------------
# Item 8: existing email routing behavior (DEMO: send to submitted email)
# is unchanged by this presentation cleanup.
# ---------------------------------------------------------------------------


def test_lead_email_routing_unchanged():
    fake_mail_instance = MagicMock()
    fake_response = MagicMock(status_code=202)
    fake_client = MagicMock()
    fake_client.send.return_value = fake_response

    with patch.dict(
        "os.environ",
        {
            "SENDGRID_API_KEY": "fake-key",
            "LEAD_NOTIFICATION_FROM": "from@example.com",
            "LEAD_NOTIFICATION_TO": "internal-team@example.com",
            "ADMIN_CONSOLE_URL": "https://console.example.com",
            "SEND_LEAD_NOTIFICATIONS": "true",
        },
        clear=False,
    ):
        with patch("sendgrid.SendGridAPIClient", return_value=fake_client) as mock_client_cls, \
             patch("sendgrid.helpers.mail.Mail", return_value=fake_mail_instance) as mock_mail_cls:
            _send(**_sample_kwargs("not_eligible"))

    # DEMO behavior preserved: routed to the applicant's submitted email, NOT
    # to LEAD_NOTIFICATION_TO. This task explicitly does not change routing.
    _, mail_kwargs = mock_mail_cls.call_args
    assert mail_kwargs["to_emails"] == "jane@example.com"
    assert mail_kwargs["from_email"] == "from@example.com"
    # Subject/body passed to Mail() are the humanized versions.
    assert "not_eligible" not in mail_kwargs["subject"]
    assert "Not Eligible" in mail_kwargs["subject"]
    mock_client_cls.assert_called_once_with("fake-key")
    fake_client.send.assert_called_once()


def test_lead_email_disabled_flag_still_skips_send():
    with patch.dict("os.environ", {"SEND_LEAD_NOTIFICATIONS": "false"}, clear=False):
        with patch("sendgrid.SendGridAPIClient") as mock_client_cls:
            send_lead_notification(**_sample_kwargs("eligible"))
    mock_client_cls.assert_not_called()
