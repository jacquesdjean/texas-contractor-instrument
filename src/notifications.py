"""Send notifications for high-priority new licenses via email and/or Slack."""

import json
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

import requests as http_requests

from src.scorer import format_phone

logger = logging.getLogger(__name__)

HIGH_PRIORITY_THRESHOLD = 90  # Score at or above this triggers a notification


def format_license_summary(records: list[dict]) -> str:
    """Format high-priority licenses into a readable text summary."""
    lines = []
    for r in records:
        phone = r.get("business_telephone") or r.get("owner_telephone") or "N/A"
        if phone != "N/A":
            phone = format_phone(phone)
        lines.append(
            f"  [{r.get('_score', 0)}] {r.get('license_type')} — "
            f"{r.get('business_name', 'Unknown')} ({r.get('business_county', '')})\n"
            f"       Owner: {r.get('owner_name', 'N/A')} | Phone: {phone}"
        )
    return "\n".join(lines)


def send_slack_notification(records: list[dict]) -> bool:
    """Post high-priority new licenses to a Slack webhook."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("SLACK_WEBHOOK_URL not set — skipping Slack notification")
        return False

    high_priority = [r for r in records if r.get("_score", 0) >= HIGH_PRIORITY_THRESHOLD]
    if not high_priority:
        logger.info("No high-priority licenses to notify about")
        return False

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"TDLR Alert: {len(high_priority)} New High-Priority License(s)",
            },
        },
        {"type": "divider"},
    ]

    for r in high_priority[:10]:  # Cap at 10 to avoid huge messages
        phone = r.get("business_telephone") or r.get("owner_telephone") or "N/A"
        if phone != "N/A":
            phone = format_phone(phone)
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{r.get('license_type')}*\nScore: {r.get('_score', 0)}"},
                {"type": "mrkdwn", "text": f"*{r.get('business_name', 'Unknown')}*\n{r.get('business_county', '')}"},
                {"type": "mrkdwn", "text": f"*Owner:* {r.get('owner_name', 'N/A')}"},
                {"type": "mrkdwn", "text": f"*Phone:* {phone}"},
            ],
        })

    if len(high_priority) > 10:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"_...and {len(high_priority) - 10} more. Check Google Sheets for the full list._",
            },
        })

    payload = {"blocks": blocks}

    try:
        resp = http_requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Slack notification sent for %d high-priority licenses", len(high_priority))
        return True
    except http_requests.RequestException as e:
        logger.error("Failed to send Slack notification: %s", e)
        return False


def send_email_notification(records: list[dict]) -> bool:
    """Send email digest of high-priority new licenses via SMTP."""
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    email_to = os.environ.get("NOTIFICATION_EMAIL")

    if not all([smtp_host, smtp_user, smtp_pass, email_to]):
        logger.debug("Email configuration incomplete — skipping email notification")
        return False

    high_priority = [r for r in records if r.get("_score", 0) >= HIGH_PRIORITY_THRESHOLD]
    if not high_priority:
        logger.info("No high-priority licenses to email about")
        return False

    subject = f"TDLR Alert: {len(high_priority)} New High-Priority Contractor License(s)"
    body = (
        f"The TDLR License Monitor detected {len(high_priority)} new high-priority "
        f"license(s) this week (score >= {HIGH_PRIORITY_THRESHOLD}):\n\n"
        f"{format_license_summary(high_priority)}\n\n"
        "See Google Sheets for the full list with all details."
    )

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Email notification sent to %s for %d high-priority licenses", email_to, len(high_priority))
        return True
    except Exception as e:
        logger.error("Failed to send email notification: %s", e)
        return False


def notify(scored_records: list[dict]) -> dict:
    """Send all configured notifications. Returns status dict."""
    results = {
        "slack_sent": send_slack_notification(scored_records),
        "email_sent": send_email_notification(scored_records),
        "high_priority_count": len([r for r in scored_records if r.get("_score", 0) >= HIGH_PRIORITY_THRESHOLD]),
    }
    return results
