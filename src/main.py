"""TDLR License Monitor — main orchestrator."""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.scraper import fetch_licenses
from src.differ import diff_snapshots
from src.scorer import score_and_sort
from src.sheets_output import push_to_sheets
from src.notifications import notify

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RUN_LOG_PATH = DATA_DIR / "run_log.json"
TSBPE_SNAPSHOT_PATH = DATA_DIR / "tsbpe_previous_snapshot.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def update_run_log(
    total_fetched: int,
    new_count: int,
    removed_count: int,
    is_first_run: bool,
    tsbpe_fetched: int = 0,
    tsbpe_new: int = 0,
    notifications: dict | None = None,
):
    """Write run metadata to run_log.json."""
    log_entry = {
        "last_run": datetime.now().isoformat(),
        "total_fetched": total_fetched,
        "new_licenses": new_count,
        "removed_licenses": removed_count,
        "is_first_run": is_first_run,
        "tsbpe_fetched": tsbpe_fetched,
        "tsbpe_new_licenses": tsbpe_new,
        "notifications": notifications or {},
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG_PATH, "w") as f:
        json.dump(log_entry, f, indent=2)
    logger.info("Run log updated: %s", log_entry)


def run_tdlr_pipeline() -> tuple[list[dict], int, int, bool]:
    """Run the TDLR license pipeline. Returns (scored_records, total, removed_count, is_first_run)."""
    try:
        current_records = fetch_licenses()
    except Exception:
        logger.exception("Failed to fetch TDLR data — aborting without updating snapshot")
        sys.exit(1)

    logger.info("Fetched %d TDLR records", len(current_records))

    new_records, removed_numbers, is_first_run = diff_snapshots(current_records)

    if is_first_run:
        logger.info("TDLR first run complete — baseline snapshot saved")
        return [], len(current_records), 0, True

    if not new_records:
        logger.info("No new TDLR licenses detected this week")
        return [], len(current_records), len(removed_numbers), False

    scored = score_and_sort(new_records)
    logger.info("Top new TDLR license: %s — %s (score %d)",
                scored[0].get("license_type"), scored[0].get("business_name"), scored[0]["_score"])
    return scored, len(current_records), len(removed_numbers), False


def run_tsbpe_pipeline() -> tuple[list[dict], int]:
    """Run the TSBPE plumbing license pipeline. Returns (scored_records, total_fetched)."""
    if not os.environ.get("ENABLE_TSBPE", "").lower() in ("1", "true", "yes"):
        logger.info("TSBPE scraper disabled (set ENABLE_TSBPE=1 to enable)")
        return [], 0

    try:
        from src.tsbpe_scraper import fetch_plumbing_licenses
        plumbing_records = fetch_plumbing_licenses()
    except Exception:
        logger.exception("Failed to fetch TSBPE data — continuing with TDLR only")
        return [], 0

    logger.info("Fetched %d TSBPE plumbing records", len(plumbing_records))

    new_records, removed_numbers, is_first_run = diff_snapshots(
        plumbing_records, TSBPE_SNAPSHOT_PATH
    )

    if is_first_run:
        logger.info("TSBPE first run — baseline snapshot saved")
        return [], len(plumbing_records)

    if not new_records:
        logger.info("No new TSBPE licenses detected this week")
        return [], len(plumbing_records)

    scored = score_and_sort(new_records)
    return scored, len(plumbing_records)


def main():
    logger.info("Starting TDLR License Monitor v2")

    # Run TDLR pipeline
    tdlr_scored, tdlr_total, tdlr_removed, is_first_run = run_tdlr_pipeline()

    # Run TSBPE pipeline
    tsbpe_scored, tsbpe_total = run_tsbpe_pipeline()

    # Combine all scored records
    all_scored = tdlr_scored + tsbpe_scored
    all_scored.sort(key=lambda r: r.get("_score", 0), reverse=True)

    if all_scored:
        push_to_sheets(all_scored)
        notification_results = notify(all_scored)
        logger.info("Notifications: %s", notification_results)
    else:
        notification_results = {}

    update_run_log(
        total_fetched=tdlr_total,
        new_count=len(tdlr_scored),
        removed_count=tdlr_removed,
        is_first_run=is_first_run,
        tsbpe_fetched=tsbpe_total,
        tsbpe_new=len(tsbpe_scored),
        notifications=notification_results,
    )

    logger.info(
        "Run complete — %d TDLR + %d TSBPE new licenses processed",
        len(tdlr_scored), len(tsbpe_scored),
    )


if __name__ == "__main__":
    main()
