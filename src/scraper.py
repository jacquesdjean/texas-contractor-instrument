"""Fetch active TDLR licenses from the Texas Open Data Portal Socrata SODA API."""

import logging
import os
import time
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

BASE_URL = "https://data.texas.gov/resource/7358-krk7.json"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

FIELDS = [
    "license_type",
    "license_number",
    "license_subtype",
    "business_name",
    "business_county",
    "business_address_line1",
    "business_city_state_zip",
    "business_telephone",
    "owner_name",
    "owner_telephone",
    "mailing_address_county",
    "license_expiration_date_mmddccyy",
    "business_mailing",
]


PAGE_SIZE = 50000


def load_config():
    """Load license type config."""
    with open(CONFIG_DIR / "license_types.yml") as f:
        license_types = yaml.safe_load(f)

    type_names = [lt["name"] for lt in license_types["license_types"]]
    return type_names


def build_query(license_types: list[str], offset: int = 0) -> dict:
    """Build Socrata SODA API query parameters (statewide, paginated)."""
    type_clause = " OR ".join(f"license_type='{t}'" for t in license_types)

    select = ", ".join(FIELDS)

    return {
        "$where": type_clause,
        "$limit": PAGE_SIZE,
        "$offset": offset,
        "$order": "license_number",
        "$select": select,
    }


def _fetch_page(params: dict, headers: dict, max_retries: int = 3) -> list[dict]:
    """Fetch a single page from the Socrata API with retry logic."""
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(BASE_URL, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning("API request failed: %s. Retrying in %ds...", e, wait)
                time.sleep(wait)
            else:
                logger.error("API request failed after %d retries: %s", max_retries, e)
                raise


def fetch_licenses(max_retries: int = 3) -> list[dict]:
    """Fetch all matching TDLR licenses from the Socrata API (statewide, paginated)."""
    license_types = load_config()

    headers = {}
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    all_records: list[dict] = []
    offset = 0

    while True:
        params = build_query(license_types, offset=offset)
        logger.info("Fetching TDLR data (offset %d)", offset)
        page = _fetch_page(params, headers, max_retries)
        all_records.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    logger.info("Fetched %d total records from TDLR API", len(all_records))
    return all_records
