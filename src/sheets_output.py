"""Push new license data to Google Sheets."""

import base64
import json
import logging
import os
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from src.scorer import format_phone

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

NEW_LICENSES_TAB = "New Licenses"
WEEKLY_SUMMARY_TAB = "Weekly Summary"

NEW_LICENSES_HEADERS = [
    "Score",
    "License Type",
    "Business Name",
    "Owner",
    "Phone",
    "City/Zip",
    "County",
    "License #",
    "Expiration",
    "Address",
    "Date Found",
]

WEEKLY_SUMMARY_HEADERS = [
    "Week Of",
    "New Electrical Contractors",
    "New Master Electricians",
    "New Journeyman",
    "New HVAC",
    "New Water Well",
    "Total New",
    "Territory",
]


def get_sheets_service():
    """Build Google Sheets API service from base64-encoded credentials."""
    creds_b64 = os.environ.get("GOOGLE_SHEETS_CREDS")
    if not creds_b64:
        return None

    creds_json = json.loads(base64.b64decode(creds_b64))
    logger.info(
        "Sheets auth: service account = %s, project = %s",
        creds_json.get("client_email", "MISSING"),
        creds_json.get("project_id", "MISSING"),
    )
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def ensure_tab_exists(service, sheet_id: str, tab_name: str):
    """Create the tab if it doesn't already exist in the spreadsheet."""
    meta = (
        service.spreadsheets()
        .get(spreadsheetId=sheet_id, fields="sheets.properties.title")
        .execute()
    )
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if tab_name not in existing:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()
        logger.info("Created tab '%s'", tab_name)


def ensure_headers(service, sheet_id: str, tab_name: str, headers: list[str]):
    """Add header row to a tab if it's empty."""
    ensure_tab_exists(service, sheet_id, tab_name)
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A1:Z1",
        )
        .execute()
    )

    if not result.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()


def record_to_row(record: dict, date_found: str) -> list:
    """Convert a scored license record to a Sheets row."""
    phone = record.get("business_telephone") or record.get("owner_telephone") or ""
    if phone:
        phone = format_phone(phone)

    return [
        record.get("_score", 0),
        record.get("license_type", ""),
        record.get("business_name", ""),
        record.get("owner_name", ""),
        phone,
        record.get("business_city_state_zip", ""),
        record.get("business_county", ""),
        record.get("license_number", ""),
        record.get("license_expiration_date_mmddccyy", ""),
        record.get("business_address_line1", ""),
        date_found,
    ]


def build_summary_row(records: list[dict], date_str: str, territory: str) -> list:
    """Build a weekly summary row from scored records."""
    counts = {
        "Electrical Contractor": 0,
        "Master Electrician": 0,
        "Journeyman Electrician": 0,
    }
    hvac_count = 0
    water_count = 0

    for r in records:
        lt = r.get("license_type", "")
        if lt in counts:
            counts[lt] += 1
        elif lt in ("A/C Contractor", "A/C Technician"):
            hvac_count += 1
        elif lt == "Water Well Driller/Pump Installer":
            water_count += 1

    return [
        date_str,
        counts["Electrical Contractor"],
        counts["Master Electrician"],
        counts["Journeyman Electrician"],
        hvac_count,
        water_count,
        len(records),
        territory,
    ]


def _normalize_sheet_id(raw: str) -> str:
    """Extract the spreadsheet ID from a full Google Sheets URL or return as-is.

    Accepts both plain IDs and full URLs like
    ``https://docs.google.com/spreadsheets/d/<ID>/edit?...``.
    """
    if "/" in raw:
        parts = raw.split("/")
        try:
            return parts[parts.index("d") + 1]
        except (ValueError, IndexError):
            pass
    return raw.strip()


def push_to_sheets(scored_records: list[dict], week_date: datetime | None = None) -> bool:
    """Push scored records to Google Sheets. Returns True on success.

    Args:
        scored_records: Scored license records to push.
        week_date: Optional override date for the week separator and
            ``Date Found`` column.  Used during first-run backfill so that
            historical batches carry the correct week date.
    """
    service = get_sheets_service()
    if service is None:
        logger.warning("Google Sheets credentials not configured — skipping Sheets output")
        return False

    raw_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not raw_id:
        logger.warning("GOOGLE_SHEET_ID not set — skipping Sheets output")
        return False

    sheet_id = _normalize_sheet_id(raw_id)
    logger.info("Sheet ID: %s...%s (len=%d)", sheet_id[:4], sheet_id[-4:], len(sheet_id))

    ref_date = week_date or datetime.now()
    date_found = ref_date.strftime("%Y-%m-%d")
    week_of = ref_date.strftime("%m/%d/%Y")

    try:
        ensure_headers(service, sheet_id, NEW_LICENSES_TAB, NEW_LICENSES_HEADERS)
        ensure_headers(service, sheet_id, WEEKLY_SUMMARY_TAB, WEEKLY_SUMMARY_HEADERS)

        # Separator row for this week's batch
        separator = [f"--- Week of {week_of} ---"] + [""] * (len(NEW_LICENSES_HEADERS) - 1)
        rows = [separator]
        for record in scored_records:
            rows.append(record_to_row(record, date_found))

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"'{NEW_LICENSES_TAB}'!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
        logger.info("Appended %d rows to '%s' tab", len(rows), NEW_LICENSES_TAB)

        # Weekly summary
        summary_row = build_summary_row(scored_records, week_of, "Central Texas")
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"'{WEEKLY_SUMMARY_TAB}'!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [summary_row]},
        ).execute()
        logger.info("Appended weekly summary row")

        return True

    except Exception:
        logger.exception("Failed to push to Google Sheets")
        return False
