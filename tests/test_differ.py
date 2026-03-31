"""Tests for the differ module."""

import json
from pathlib import Path

import pytest

from src.differ import (
    find_new_licenses,
    find_removed_licenses,
    diff_snapshots,
    load_snapshot,
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


class TestDiffSnapshots:
    def test_first_run_creates_baseline(self, sample_records, tmp_path):
        snapshot_path = tmp_path / "snapshot.json"
        new_records, removed, is_first_run = diff_snapshots(sample_records, snapshot_path)

        assert is_first_run is True
        assert new_records == []
        assert removed == set()
        assert snapshot_path.exists()

        # Verify snapshot contents
        with open(snapshot_path) as f:
            saved = json.load(f)
        assert len(saved) == len(sample_records)

    def test_second_run_detects_new(self, sample_records, tmp_path):
        snapshot_path = tmp_path / "snapshot.json"

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
        snapshot_path = tmp_path / "snapshot.json"

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
