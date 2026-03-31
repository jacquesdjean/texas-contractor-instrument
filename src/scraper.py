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


def load_config():
    """Load territory and license type configs."""
    with open(CONFIG_DIR / "territory.yml") as f:
        territory = yaml.safe_load(f)
    with open(CONFIG_DIR / "license_types.yml") as f:
        license_types = yaml.safe_load(f)

    counties = territory["primary_counties"] + territory["secondary_counties"]
    type_names = [lt["name"] for lt in license_types["license_types"]]
    return counties, type_names


def build_query(counties: list[str], license_types: list[str]) -> dict:
    """Build Socrata SODA API query parameters."""
    county_clause = " OR ".join(f"business_county='{c}'" for c in counties)
    type_clause = " OR ".join(f"license_type='{t}'" for t in license_types)
    where = f"({county_clause}) AND ({type_clause})"

    select = ", ".join(FIELDS)

    return {
        "$where": where,
        "$limit": 50000,
        "$order": "license_number",
        "$select": select,
    }


def fetch_licenses(max_retries: int = 3) -> list[dict]:
    """Fetch all matching TDLR licenses from the Socrata API with retry logic."""
    counties, license_types = load_config()
    params = build_query(counties, license_types)

    headers = {}
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    for attempt in range(max_retries + 1):
        try:
            logger.info("Fetching TDLR data (attempt %d/%d)", attempt + 1, max_retries + 1)
            response = requests.get(BASE_URL, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            records = response.json()
            logger.info("Fetched %d records from TDLR API", len(records))
            return records
        except requests.RequestException as e:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning("API request failed: %s. Retrying in %ds...", e, wait)
                time.sleep(wait)
            else:
                logger.error("API request failed after %d retries: %s", max_retries, e)
                raise
