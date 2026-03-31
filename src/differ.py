"""Compare TDLR snapshots to detect new, removed, and reinstated licenses."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SNAPSHOT_PATH = DATA_DIR / "previous_snapshot.json"


def load_snapshot(path: Path = SNAPSHOT_PATH) -> set[str] | None:
    """Load previous snapshot of license numbers. Returns None if no snapshot exists."""
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return set(data)


def save_snapshot(license_numbers: set[str], path: Path = SNAPSHOT_PATH) -> None:
    """Save current license numbers to snapshot file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(license_numbers), f)
    logger.info("Saved snapshot with %d license numbers", len(license_numbers))


def find_new_licenses(
    current_records: list[dict], previous_license_numbers: set[str]
) -> list[dict]:
    """Return records whose license_number was NOT in the previous snapshot."""
    return [
        r for r in current_records
        if r.get("license_number") not in previous_license_numbers
    ]


def find_removed_licenses(
    current_license_numbers: set[str], previous_license_numbers: set[str]
) -> set[str]:
    """Return license numbers that were in the previous snapshot but not current.
    These may be expired or revoked licenses."""
    removed = previous_license_numbers - current_license_numbers
    if removed:
        logger.info("Detected %d removed/expired licenses", len(removed))
    return removed


def diff_snapshots(current_records: list[dict], snapshot_path: Path = SNAPSHOT_PATH):
    """Run the full diff pipeline.

    Returns:
        tuple: (new_records, removed_numbers, is_first_run)
    """
    current_numbers = {r["license_number"] for r in current_records if "license_number" in r}
    previous_numbers = load_snapshot(snapshot_path)

    if previous_numbers is None:
        logger.info(
            "First run — baseline snapshot created. "
            "New licenses will be detected starting next week."
        )
        save_snapshot(current_numbers, snapshot_path)
        return [], set(), True

    new_records = find_new_licenses(current_records, previous_numbers)
    removed_numbers = find_removed_licenses(current_numbers, previous_numbers)

    logger.info("Found %d new licenses, %d removed", len(new_records), len(removed_numbers))

    save_snapshot(current_numbers, snapshot_path)
    return new_records, removed_numbers, False
