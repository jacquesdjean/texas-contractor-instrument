"""TDLR License Monitor — main orchestrator."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.scraper import fetch_licenses
from src.differ import diff_snapshots
from src.scorer import score_and_sort
from src.sheets_output import push_to_sheets

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RUN_LOG_PATH = DATA_DIR / "run_log.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def update_run_log(total_fetched: int, new_count: int, removed_count: int, is_first_run: bool):
    """Write run metadata to run_log.json."""
    log_entry = {
        "last_run": datetime.now().isoformat(),
        "total_fetched": total_fetched,
        "new_licenses": new_count,
        "removed_licenses": removed_count,
        "is_first_run": is_first_run,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG_PATH, "w") as f:
        json.dump(log_entry, f, indent=2)
    logger.info("Run log updated: %s", log_entry)


def main():
    logger.info("Starting TDLR License Monitor")

    # Fetch current data
    try:
        current_records = fetch_licenses()
    except Exception:
        logger.exception("Failed to fetch TDLR data — aborting without updating snapshot")
        sys.exit(1)

    logger.info("Fetched %d total records", len(current_records))

    # Diff against previous snapshot
    new_records, removed_numbers, is_first_run = diff_snapshots(current_records)

    if is_first_run:
        update_run_log(len(current_records), 0, 0, True)
        logger.info("First run complete — baseline snapshot saved")
        return

    if not new_records:
        logger.info("No new licenses detected this week")
        update_run_log(len(current_records), 0, len(removed_numbers), False)
        return

    # Score and rank
    scored = score_and_sort(new_records)
    logger.info("Top new license: %s — %s (score %d)",
                scored[0].get("license_type"), scored[0].get("business_name"), scored[0]["_score"])

    # Push to Google Sheets
    push_to_sheets(scored)

    update_run_log(len(current_records), len(new_records), len(removed_numbers), False)
    logger.info("Run complete — %d new licenses processed", len(new_records))


if __name__ == "__main__":
    main()
