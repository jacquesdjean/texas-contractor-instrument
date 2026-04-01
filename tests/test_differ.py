"""Tests for the differ module."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.differ import (
    bucket_by_week,
    diff_snapshots,
    find_new_licenses,
    find_reinstated_licenses,
    find_removed_licenses,
    load_historical,
    load_snapshot,
    save_historical,
    save_snapshot,
)


@pytest.fixture
def sample_records():
    fixtures_path = Path(__file__).parent / "fixtures" / "sample_tdlr_response.json"
    with open(fixtures_path) as f:
        return json.load(f)


@pytest.fixture
def previous_numbers():
    """A set of license numbers representing last week's snapshot."""
    return {"19901", "20501", "31005", "42100", "42200", "55010", "60300", "19950"}


class TestFindNewLicenses:
    def test_detects_new_licenses(self, sample_records, previous_numbers):
        new = find_new_licenses(sample_records, previous_numbers)
        new_numbers = {r["license_number"] for r in new}
        # Records not in previous: 42150, 19975, 31050, 20550
        assert new_numbers == {"42150", "19975", "31050", "20550"}

    def test_no_new_when_all_exist(self, sample_records):
        all_numbers = {r["license_number"] for r in sample_records}
        new = find_new_licenses(sample_records, all_numbers)
        assert new == []

    def test_all_new_when_empty_previous(self, sample_records):
        new = find_new_licenses(sample_records, set())
        assert len(new) == len(sample_records)


class TestFindRemovedLicenses:
    def test_detects_removed(self):
        current = {"A", "B", "C"}
        previous = {"A", "B", "D", "E"}
        removed = find_removed_licenses(current, previous)
        assert removed == {"D", "E"}

    def test_no_removals(self):
        current = {"A", "B", "C"}
        previous = {"A", "B"}
        removed = find_removed_licenses(current, previous)
        assert removed == set()


class TestFindReinstatedLicenses:
    def test_detects_reinstated(self):
        # License "X" was seen historically, disappeared, now back as "new"
        new_records = [
            {"license_number": "X"},
            {"license_number": "Y"},
        ]
        historical = {"X", "A", "B"}  # X was seen before
        reinstated = find_reinstated_licenses(new_records, historical)
        assert len(reinstated) == 1
        assert reinstated[0]["license_number"] == "X"

    def test_no_reinstated_when_all_truly_new(self):
        new_records = [{"license_number": "Z"}]
        historical = {"A", "B"}
        reinstated = find_reinstated_licenses(new_records, historical)
        assert reinstated == []

    def test_empty_historical(self):
        new_records = [{"license_number": "A"}]
        reinstated = find_reinstated_licenses(new_records, set())
        assert reinstated == []


class TestDiffSnapshots:
    def test_first_run_creates_baseline(self, sample_records, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"
        new_records, removed, is_first_run = diff_snapshots(sample_records, snapshot_path)

        assert is_first_run is True
        assert new_records == []
        assert removed == set()
        assert snapshot_path.exists()

        # Verify snapshot contents
        with open(snapshot_path) as f:
            saved = json.load(f)
        assert len(saved) == len(sample_records)

        # Verify historical file was created
        history_path = tmp_path / "historical_licenses.json"
        assert history_path.exists()

    def test_second_run_detects_new(self, sample_records, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"

        # First run: baseline with subset
        baseline_numbers = [r["license_number"] for r in sample_records[:8]]
        save_snapshot(set(baseline_numbers), snapshot_path)

        # Second run: full set — should detect the remaining as new
        new_records, removed, is_first_run = diff_snapshots(sample_records, snapshot_path)

        assert is_first_run is False
        assert len(new_records) == len(sample_records) - 8
        new_numbers = {r["license_number"] for r in new_records}
        expected_new = {r["license_number"] for r in sample_records[8:]}
        assert new_numbers == expected_new

    def test_detects_removed_licenses(self, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"

        # Previous had licenses A, B, C
        save_snapshot({"A", "B", "C"}, snapshot_path)

        # Current only has A, B (C was removed)
        current = [
            {"license_number": "A"},
            {"license_number": "B"},
        ]
        new_records, removed, is_first_run = diff_snapshots(current, snapshot_path)

        assert is_first_run is False
        assert removed == {"C"}
        assert new_records == []

    def test_flags_reinstated_licenses(self, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"
        history_path = tmp_path / "historical_licenses.json"

        # Historical: A, B, C were all seen at some point
        save_historical({"A", "B", "C"}, history_path)
        # Previous snapshot: only A, B (C disappeared last week)
        save_snapshot({"A", "B"}, snapshot_path)

        # Current: A, B, C are all back — C is reinstated
        current = [
            {"license_number": "A"},
            {"license_number": "B"},
            {"license_number": "C"},
        ]
        new_records, removed, is_first_run = diff_snapshots(current, snapshot_path)

        assert is_first_run is False
        assert len(new_records) == 1
        assert new_records[0]["license_number"] == "C"
        assert new_records[0]["_reinstated"] is True

    def test_new_license_not_flagged_reinstated(self, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"
        history_path = tmp_path / "historical_licenses.json"

        save_historical({"A", "B"}, history_path)
        save_snapshot({"A", "B"}, snapshot_path)

        # D is truly new — never seen before
        current = [
            {"license_number": "A"},
            {"license_number": "B"},
            {"license_number": "D"},
        ]
        new_records, removed, is_first_run = diff_snapshots(current, snapshot_path)

        assert len(new_records) == 1
        assert new_records[0]["license_number"] == "D"
        assert new_records[0]["_reinstated"] is False


class TestSnapshotIO:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "test_snapshot.json"
        numbers = {"111", "222", "333"}
        save_snapshot(numbers, path)
        loaded = load_snapshot(path)
        assert loaded == numbers

    def test_load_nonexistent(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        assert load_snapshot(path) is None


class TestHistoricalIO:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "historical.json"
        numbers = {"A", "B", "C"}
        save_historical(numbers, path)
        loaded = load_historical(path)
        assert loaded == numbers

    def test_load_nonexistent(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        assert load_historical(path) == set()

    def test_historical_accumulates(self, tmp_path):
        path = tmp_path / "historical.json"
        save_historical({"A", "B"}, path)
        existing = load_historical(path)
        save_historical(existing | {"C", "D"}, path)
        loaded = load_historical(path)
        assert loaded == {"A", "B", "C", "D"}


class TestBucketByWeek:
    def test_records_land_in_correct_buckets(self):
        now = datetime.now(UTC)
        records = [
            {"license_number": "A", "_created_at": (now - timedelta(days=2)).isoformat()},
            {"license_number": "B", "_created_at": (now - timedelta(days=10)).isoformat()},
            {"license_number": "C", "_created_at": (now - timedelta(days=20)).isoformat()},
        ]
        buckets = bucket_by_week(records, weeks=4)
        assert len(buckets) == 4
        # Most recent bucket (week 4) should have record A
        assert any(r["license_number"] == "A" for r in buckets[3][1])
        # Second-most-recent (week 3) should have record B
        assert any(r["license_number"] == "B" for r in buckets[2][1])

    def test_strips_created_at(self):
        now = datetime.now(UTC)
        records = [
            {"license_number": "X", "_created_at": (now - timedelta(days=1)).isoformat()},
        ]
        buckets = bucket_by_week(records, weeks=4)
        for _, bucket in buckets:
            for record in bucket:
                assert "_created_at" not in record

    def test_empty_input(self):
        buckets = bucket_by_week([], weeks=4)
        assert len(buckets) == 4
        assert all(len(b) == 0 for _, b in buckets)

    def test_missing_created_at_goes_to_last_bucket(self):
        records = [{"license_number": "Z"}]
        buckets = bucket_by_week(records, weeks=4)
        assert len(buckets[3][1]) == 1
        assert buckets[3][1][0]["license_number"] == "Z"

    def test_returns_week_start_dates(self):
        buckets = bucket_by_week([], weeks=4)
        # Week starts should be in chronological order
        dates = [d for d, _ in buckets]
        assert dates == sorted(dates)


class TestDiffSnapshotsWithRecentRecords:
    def test_first_run_returns_recent_records(self, sample_records, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"
        recent = [{"license_number": "NEW1"}, {"license_number": "NEW2"}]

        new_records, removed, is_first_run = diff_snapshots(
            sample_records, snapshot_path, recent_records=recent
        )

        assert is_first_run is True
        assert len(new_records) == 2
        assert {r["license_number"] for r in new_records} == {"NEW1", "NEW2"}
        # Full snapshot should still be saved
        assert snapshot_path.exists()
        with open(snapshot_path) as f:
            saved = json.load(f)
        assert len(saved) == len(sample_records)

    def test_first_run_without_recent_returns_empty(self, sample_records, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"

        new_records, removed, is_first_run = diff_snapshots(
            sample_records, snapshot_path, recent_records=None
        )

        assert is_first_run is True
        assert new_records == []

    def test_recent_records_ignored_on_subsequent_run(self, sample_records, tmp_path):
        snapshot_path = tmp_path / "previous_snapshot.json"
        # Create a baseline first
        save_snapshot({r["license_number"] for r in sample_records[:8]}, snapshot_path)

        recent = [{"license_number": "IGNORED"}]
        new_records, removed, is_first_run = diff_snapshots(
            sample_records, snapshot_path, recent_records=recent
        )

        # recent_records should be ignored on non-first run
        assert is_first_run is False
        assert not any(r["license_number"] == "IGNORED" for r in new_records)
