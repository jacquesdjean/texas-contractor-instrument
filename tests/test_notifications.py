"""Tests for the notifications module."""

from unittest.mock import patch, MagicMock

import pytest

from src.notifications import (
    format_license_summary,
    send_slack_notification,
    send_email_notification,
    notify,
    HIGH_PRIORITY_THRESHOLD,
)


@pytest.fixture
def high_priority_records():
    return [
        {
            "license_type": "Electrical Contractor",
            "business_name": "ACME ELECTRIC LLC",
            "business_county": "TRAVIS",
            "business_telephone": "5125551234",
            "owner_name": "JOHN DOE",
            "owner_telephone": "5125551234",
            "_score": 130,
        },
        {
            "license_type": "A/C Contractor",
            "business_name": "COOL AIR INC",
            "business_county": "WILLIAMSON",
            "business_telephone": "5125559876",
            "owner_name": "JANE SMITH",
            "owner_telephone": "5125559876",
            "_score": 120,
        },
    ]


@pytest.fixture
def low_priority_records():
    return [
        {
            "license_type": "Journeyman Electrician",
            "business_name": "JOE ELECTRIC",
            "business_county": "MILAM",
            "business_telephone": "",
            "owner_name": "JOE",
            "owner_telephone": "",
            "_score": 30,
        },
    ]


class TestFormatLicenseSummary:
    def test_formats_records(self, high_priority_records):
        summary = format_license_summary(high_priority_records)
        assert "ACME ELECTRIC LLC" in summary
        assert "Electrical Contractor" in summary
        assert "(512) 555-1234" in summary

    def test_handles_no_phone(self, low_priority_records):
        summary = format_license_summary(low_priority_records)
        assert "N/A" in summary


class TestSlackNotification:
    @patch.dict("os.environ", {"SLACK_WEBHOOK_URL": ""})
    def test_skips_when_no_url(self, high_priority_records):
        assert send_slack_notification(high_priority_records) is False

    @patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"})
    def test_skips_when_no_high_priority(self, low_priority_records):
        assert send_slack_notification(low_priority_records) is False

    @patch("src.notifications.http_requests.post")
    @patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"})
    def test_sends_when_high_priority(self, mock_post, high_priority_records):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        result = send_slack_notification(high_priority_records)
        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "blocks" in payload


class TestEmailNotification:
    @patch.dict("os.environ", {}, clear=True)
    def test_skips_when_not_configured(self, high_priority_records):
        assert send_email_notification(high_priority_records) is False

    @patch.dict("os.environ", {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user@test.com",
        "SMTP_PASS": "pass",
        "NOTIFICATION_EMAIL": "to@test.com",
    })
    def test_skips_when_no_high_priority(self, low_priority_records):
        assert send_email_notification(low_priority_records) is False

    @patch("src.notifications.smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user@test.com",
        "SMTP_PASS": "pass",
        "NOTIFICATION_EMAIL": "to@test.com",
    })
    def test_sends_email_for_high_priority(self, mock_smtp_class, high_priority_records):
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = send_email_notification(high_priority_records)
        assert result is True
        mock_server.send_message.assert_called_once()


class TestNotify:
    @patch("src.notifications.send_slack_notification", return_value=False)
    @patch("src.notifications.send_email_notification", return_value=False)
    def test_returns_status_dict(self, mock_email, mock_slack, high_priority_records):
        results = notify(high_priority_records)
        assert "slack_sent" in results
        assert "email_sent" in results
        assert results["high_priority_count"] == 2

    @patch("src.notifications.send_slack_notification", return_value=False)
    @patch("src.notifications.send_email_notification", return_value=False)
    def test_zero_high_priority(self, mock_email, mock_slack, low_priority_records):
        results = notify(low_priority_records)
        assert results["high_priority_count"] == 0
