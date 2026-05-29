"""Lead notification emails — internal alerts when a QIQ demo completes.

Requires env vars:
  SENDGRID_API_KEY
  LEAD_NOTIFICATION_FROM (sender: e.g. jude@nimbleai.email)
  ADMIN_CONSOLE_URL      (link to admin console)

Optional:
  SEND_LEAD_NOTIFICATIONS (default "true"; set to "false" to disable)

NOTE — DEMO BEHAVIOR:
  The notification is sent TO the email address the prospect submitted in Layer 0,
  so the person running the demo experiences receiving the lead alert themselves.
  LEAD_NOTIFICATION_TO env var is read but not used in this demo flow.
  For production, replace `to_email = email` with `to_email = os.getenv("LEAD_NOTIFICATION_TO", "").strip()`
  and add it back to the missing-vars check.

All failures are logged and swallowed — email never blocks record saving.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def send_lead_notification(
    *,
    full_name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    pathway: Optional[str],
    status: Optional[str],
    created_at: Optional[str] = None,
) -> None:
    """Send an internal lead alert email. Never raises."""
    try:
        _send(
            full_name=full_name,
            email=email,
            phone=phone,
            pathway=pathway,
            status=status,
            created_at=created_at,
        )
    except Exception as exc:
        logger.error("Lead notification failed (non-fatal): %s", exc, exc_info=True)


def _send(
    *,
    full_name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    pathway: Optional[str],
    status: Optional[str],
    created_at: Optional[str],
) -> None:
    enabled = os.getenv("SEND_LEAD_NOTIFICATIONS", "true").strip().lower()
    if enabled == "false":
        logger.info("Lead notifications disabled (SEND_LEAD_NOTIFICATIONS=false)")
        return

    api_key     = os.getenv("SENDGRID_API_KEY", "").strip()
    _unused_to  = os.getenv("LEAD_NOTIFICATION_TO", "").strip()  # kept for future production use
    from_email  = os.getenv("LEAD_NOTIFICATION_FROM", "").strip()
    console_url = os.getenv("ADMIN_CONSOLE_URL", "").strip()

    missing = [k for k, v in {
        "SENDGRID_API_KEY":        api_key,
        "LEAD_NOTIFICATION_FROM":  from_email,
    }.items() if not v]

    if missing:
        logger.warning(
            "Lead notification skipped — missing env vars: %s", ", ".join(missing)
        )
        return

    # DEMO: send to the prospect's own email so the demo runner sees the alert.
    # Production: replace this with `to_email = os.getenv("LEAD_NOTIFICATION_TO", "").strip()`
    to_email = (email or "").strip()
    if not to_email or "@" not in to_email:
        logger.warning("Lead notification skipped — submitted email missing or invalid: %r", email)
        return

    try:
        import sendgrid as sg_mod
        from sendgrid.helpers.mail import Mail
    except ImportError:
        logger.warning("Lead notification skipped — sendgrid package not installed")
        return

    ts = created_at or datetime.now(timezone.utc).isoformat()
    subject = f"New QIQ Demo Completed — {status or 'unknown'}"
    body = (
        "New QIQ eligibility check completed.\n\n"
        f"Name:     {full_name or '—'}\n"
        f"Email:    {email or '—'}\n"
        f"Phone:    {phone or '—'}\n"
        f"Pathway:  {pathway or '—'}\n"
        f"Status:   {status or '—'}\n"
        f"Created:  {ts}\n"
    )
    if console_url:
        body += f"\nView in console:\n{console_url}\n"

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )

    client = sg_mod.SendGridAPIClient(api_key)
    response = client.send(message)
    logger.info(
        "Lead notification sent to %s (status %s)", to_email, response.status_code
    )
