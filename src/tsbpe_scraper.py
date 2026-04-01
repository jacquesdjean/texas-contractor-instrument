"""Fetch plumbing licenses from the Texas State Board of Plumbing Examiners (TSBPE).

TSBPE publishes license data on the Texas Open Data Portal via Socrata.
Dataset: https://data.texas.gov/dataset/TSBPE-License-Data/

This module mirrors the interface of scraper.py so the differ and scorer
can process TSBPE records identically to TDLR records.
"""

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

TSBPE_BASE_URL = "https://data.texas.gov/resource/qced-zkby.json"

PAGE_SIZE = 50000

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


def build_tsbpe_query(offset: int = 0) -> dict:
    """Build SODA API query for TSBPE plumbing licenses (statewide, paginated)."""
    type_clause = " OR ".join(f"license_type='{t}'" for t in PLUMBING_LICENSE_TYPES)

    return {
        "$where": type_clause,
        "$limit": PAGE_SIZE,
        "$offset": offset,
        "$order": "license_number",
    }


def _normalize_record(r: dict) -> dict:
    """Normalize a TSBPE record to match TDLR shape."""
    return {
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


def _fetch_page(params: dict, headers: dict, max_retries: int = 3) -> list[dict]:
    """Fetch a single page from the TSBPE Socrata API with retry logic."""
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(TSBPE_BASE_URL, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning("TSBPE API request failed: %s. Retrying in %ds...", e, wait)
                time.sleep(wait)
            else:
                logger.error("TSBPE API request failed after %d retries: %s", max_retries, e)
                raise


def fetch_plumbing_licenses(max_retries: int = 3) -> list[dict]:
    """Fetch all plumbing licenses from TSBPE via Socrata API (statewide, paginated)."""
    headers = {}
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    all_records: list[dict] = []
    offset = 0

    while True:
        params = build_tsbpe_query(offset=offset)
        logger.info("Fetching TSBPE plumbing data (offset %d)", offset)
        page = _fetch_page(params, headers, max_retries)
        all_records.extend(_normalize_record(r) for r in page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    logger.info("Fetched %d plumbing records from TSBPE", len(all_records))
    return all_records
