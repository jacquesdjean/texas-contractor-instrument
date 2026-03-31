"""Fetch plumbing licenses from the Texas State Board of Plumbing Examiners (TSBPE).

TSBPE publishes license data on the Texas Open Data Portal via Socrata.
Dataset: https://data.texas.gov/dataset/TSBPE-License-Data/

This module mirrors the interface of scraper.py so the differ and scorer
can process TSBPE records identically to TDLR records.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

# TSBPE dataset on Texas Open Data Portal
BASE_URL = "https://data.texas.gov/resource/7358-krk7.json"
# Note: The actual TSBPE dataset ID will need to be confirmed.
# TSBPE may use a different dataset identifier. For now, this module
# provides the framework — the correct endpoint must be verified at
# https://data.texas.gov by searching for "TSBPE" or "plumbing".

TSBPE_BASE_URL = "https://data.texas.gov/resource/qced-zkby.json"

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# TSBPE license types relevant to our territory
PLUMBING_LICENSE_TYPES = [
    "Master Plumber",
    "Journeyman Plumber",
    "Plumber's Apprentice",
    "Tradesman Plumber-Limited",
    "Residential Utilities Installer",
    "Drain Cleaner",
    "Drain Cleaner-Restricted",
    "Water Supply Protection Specialist",
]

# Fields available in TSBPE dataset (may differ from TDLR — verify against actual API)
TSBPE_FIELDS = [
    "license_type",
    "license_number",
    "business_name",
    "business_county",
    "business_address_line1",
    "business_city_state_zip",
    "business_telephone",
    "owner_name",
    "owner_telephone",
    "license_expiration_date_mmddccyy",
]


def load_territory() -> list[str]:
    """Load territory counties from config."""
    with open(CONFIG_DIR / "territory.yml") as f:
        territory = yaml.safe_load(f)
    return territory["primary_counties"] + territory["secondary_counties"]


def build_tsbpe_query(counties: list[str]) -> dict:
    """Build SODA API query for TSBPE plumbing licenses."""
    county_clause = " OR ".join(f"business_county='{c}'" for c in counties)
    type_clause = " OR ".join(f"license_type='{t}'" for t in PLUMBING_LICENSE_TYPES)
    where = f"({county_clause}) AND ({type_clause})"

    return {
        "$where": where,
        "$limit": 50000,
        "$order": "license_number",
    }


def _fetch_tsbpe_with_retry(params: dict, max_retries: int = 3, label: str = "TSBPE") -> list[dict]:
    """Shared fetch logic with retry/backoff for TSBPE Socrata API calls."""
    headers = {}
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                "Fetching %s plumbing data (attempt %d/%d)", label, attempt + 1, max_retries + 1
            )
            response = requests.get(TSBPE_BASE_URL, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning("%s API request failed: %s. Retrying in %ds...", label, e, wait)
                time.sleep(wait)
            else:
                logger.error("%s API request failed after %d retries: %s", label, max_retries, e)
                raise


def _normalize_tsbpe(records: list[dict], preserve_created_at: bool = False) -> list[dict]:
    """Normalize TSBPE records to match TDLR shape."""
    normalized = []
    for r in records:
        entry = {
            "license_type": r.get("license_type", ""),
            "license_number": f"TSBPE-{r.get('license_number', '')}",
            "license_subtype": "",
            "business_name": r.get("business_name", ""),
            "business_county": r.get("business_county", ""),
            "business_address_line1": r.get("business_address_line1", ""),
            "business_city_state_zip": r.get("business_city_state_zip", ""),
            "business_telephone": r.get("business_telephone", ""),
            "owner_name": r.get("owner_name", ""),
            "owner_telephone": r.get("owner_telephone", ""),
            "mailing_address_county": r.get("mailing_address_county", ""),
            "license_expiration_date_mmddccyy": r.get("license_expiration_date_mmddccyy", ""),
            "business_mailing": r.get("business_mailing"),
            "_source": "TSBPE",
        }
        if preserve_created_at:
            entry["_created_at"] = r.get(":created_at", "")
        normalized.append(entry)
    return normalized


def fetch_plumbing_licenses(max_retries: int = 3) -> list[dict]:
    """Fetch plumbing licenses from TSBPE via Socrata API.

    Returns records in the same shape as TDLR records for compatibility
    with the differ and scorer modules.
    """
    counties = load_territory()
    params = build_tsbpe_query(counties)
    records = _fetch_tsbpe_with_retry(params, max_retries, label="TSBPE")
    normalized = _normalize_tsbpe(records)
    logger.info("Fetched %d plumbing records from TSBPE", len(normalized))
    return normalized


def fetch_recent_plumbing_licenses(weeks: int = 4, max_retries: int = 3) -> list[dict]:
    """Fetch TSBPE plumbing licenses created in the last *weeks* weeks.

    Uses the Socrata ``:created_at`` system field.  Each returned record
    carries a temporary ``_created_at`` key for weekly bucketing.
    """
    counties = load_territory()
    params = build_tsbpe_query(counties)

    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).strftime("%Y-%m-%dT%H:%M:%S")
    params["$where"] += f" AND :created_at >= '{cutoff}'"
    params["$order"] = ":created_at"

    records = _fetch_tsbpe_with_retry(params, max_retries, label="TSBPE-recent")
    normalized = _normalize_tsbpe(records, preserve_created_at=True)
    logger.info("Fetched %d recent plumbing records from TSBPE", len(normalized))
    return normalized
