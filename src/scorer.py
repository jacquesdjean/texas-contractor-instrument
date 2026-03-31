"""Score and rank new licenses by recruitment value."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_scoring_config() -> dict:
    """Load scoring weights from config."""
    with open(CONFIG_DIR / "scoring.yml") as f:
        return yaml.safe_load(f)


def format_phone(raw_phone: str) -> str:
    """Format raw digit phone number as (XXX) XXX-XXXX."""
    digits = "".join(c for c in raw_phone if c.isdigit())
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return raw_phone


def score_record(record: dict, config: dict) -> int:
    """Calculate recruitment score for a single license record."""
    license_type = record.get("license_type", "")
    base_score = config["license_type_scores"].get(license_type, 0)

    bonuses = config["bonuses"]
    bonus = 0

    phone = record.get("business_telephone") or record.get("owner_telephone")
    if phone and phone.strip():
        bonus += bonuses["has_phone_number"]

    county = record.get("business_county", "")
    if county in config["primary_counties"]:
        bonus += bonuses["in_primary_county"]

    geo = record.get("business_mailing")
    if geo and isinstance(geo, dict) and geo.get("coordinates"):
        bonus += bonuses["has_geocoordinates"]

    return base_score + bonus


def score_and_sort(records: list[dict]) -> list[dict]:
    """Score all records and return sorted by score descending."""
    config = load_scoring_config()

    scored = []
    for record in records:
        score = score_record(record, config)
        scored_record = {**record, "_score": score}
        scored.append(scored_record)

    scored.sort(key=lambda r: r["_score"], reverse=True)
    logger.info(
        "Scored %d records (max=%d, min=%d)",
        len(scored),
        scored[0]["_score"] if scored else 0,
        scored[-1]["_score"] if scored else 0,
    )
    return scored
