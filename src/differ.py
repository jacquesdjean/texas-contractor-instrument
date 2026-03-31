"""Compare TDLR snapshots to detect new, removed, and reinstated licenses."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SNAPSHOT_PATH = DATA_DIR / "previous_snapshot.json"
HISTORY_PATH = DATA_DIR / "historical_licenses.json"


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


def load_historical(path: Path = HISTORY_PATH) -> set[str]:
    """Load the set of all license numbers ever seen."""
    if not path.exists():
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_historical(license_numbers: set[str], path: Path = HISTORY_PATH) -> None:
    """Save the cumulative set of all license numbers ever seen."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(license_numbers), f)


def find_new_licenses(
    current_records: list[dict], previous_license_numbers: set[str]
) -> list[dict]:
    """Return records whose license_number was NOT in the previous snapshot."""
    return [r for r in current_records if r.get("license_number") not in previous_license_numbers]


def find_removed_licenses(
    current_license_numbers: set[str], previous_license_numbers: set[str]
) -> set[str]:
    """Return license numbers that were in the previous snapshot but not current.
    These may be expired or revoked licenses."""
    removed = previous_license_numbers - current_license_numbers
    if removed:
        logger.info("Detected %d removed/expired licenses", len(removed))
    return removed


def find_reinstated_licenses(new_records: list[dict], historical_numbers: set[str]) -> list[dict]:
    """Identify licenses that are 'new' this week but have been seen in a prior run.
    These are likely reinstated after expiration/revocation."""
    reinstated = [r for r in new_records if r.get("license_number") in historical_numbers]
    if reinstated:
        logger.info("Detected %d reinstated licenses", len(reinstated))
    return reinstated


def diff_snapshots(current_records: list[dict], snapshot_path: Path = SNAPSHOT_PATH):
    """Run the full diff pipeline.

    Returns:
        tuple: (new_records, removed_numbers, is_first_run)
        New records that are reinstated will have a '_reinstated' flag set to True.
    """
    current_numbers = {r["license_number"] for r in current_records if "license_number" in r}
    previous_numbers = load_snapshot(snapshot_path)

    # Derive historical path from snapshot path
    history_path = snapshot_path.parent / snapshot_path.name.replace(
        "previous_snapshot", "historical_licenses"
    )
    if snapshot_path == SNAPSHOT_PATH:
        history_path = HISTORY_PATH

    historical = load_historical(history_path)

    if previous_numbers is None:
        logger.info(
            "First run — baseline snapshot created. "
            "New licenses will be detected starting next week."
        )
        save_snapshot(current_numbers, snapshot_path)
        # Initialize historical with current
        save_historical(current_numbers | historical, history_path)
        return [], set(), True

    new_records = find_new_licenses(current_records, previous_numbers)
    removed_numbers = find_removed_licenses(current_numbers, previous_numbers)

    # Flag reinstated licenses
    reinstated = find_reinstated_licenses(new_records, historical)
    reinstated_numbers = {r["license_number"] for r in reinstated}
    for record in new_records:
        record["_reinstated"] = record.get("license_number") in reinstated_numbers

    logger.info(
        "Found %d new licenses (%d reinstated), %d removed",
        len(new_records),
        len(reinstated),
        len(removed_numbers),
    )

    save_snapshot(current_numbers, snapshot_path)
    # Update historical with all ever-seen license numbers
    save_historical(current_numbers | historical, history_path)

    return new_records, removed_numbers, False
