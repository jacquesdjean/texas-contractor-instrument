"""Tests for the scorer module."""

import json
from pathlib import Path

import pytest

from src.scorer import format_phone, load_scoring_config, score_and_sort, score_record


@pytest.fixture
def config():
    return load_scoring_config()


@pytest.fixture
def sample_records():
    fixtures_path = Path(__file__).parent / "fixtures" / "sample_tdlr_response.json"
    with open(fixtures_path) as f:
        return json.load(f)


class TestScoreRecord:
    def test_electrical_contractor_primary_county_full_bonus(self, config):
        record = {
            "license_type": "Electrical Contractor",
            "business_county": "TRAVIS",
            "business_telephone": "5126528463",
            "business_mailing": {"type": "Point", "coordinates": [-97.74, 30.26]},
        }
        score = score_record(record, config)
        # 100 (base) + 10 (phone) + 15 (primary county) + 5 (geo) = 130
        assert score == 130

    def test_electrical_contractor_secondary_county_no_geo(self, config):
        record = {
            "license_type": "Electrical Contractor",
            "business_county": "BASTROP",
            "business_telephone": "5125554444",
            "business_mailing": None,
        }
        score = score_record(record, config)
        # 100 (base) + 10 (phone) = 110
        assert score == 110

    def test_journeyman_no_phone_no_geo(self, config):
        record = {
            "license_type": "Journeyman Electrician",
            "business_county": "MILAM",
            "business_telephone": "",
            "owner_telephone": "",
            "business_mailing": None,
        }
        score = score_record(record, config)
        # 30 (base) + 0 = 30
        assert score == 30

    def test_ac_contractor_primary_county(self, config):
        record = {
            "license_type": "A/C Contractor",
            "business_county": "TRAVIS",
            "business_telephone": "5125554321",
            "business_mailing": {"type": "Point", "coordinates": [-97.74, 30.36]},
        }
        score = score_record(record, config)
        # 90 + 10 + 15 + 5 = 120
        assert score == 120

    def test_water_well_secondary_county(self, config):
        record = {
            "license_type": "Water Well Driller/Pump Installer",
            "business_county": "BURNET",
            "business_telephone": "5125552222",
            "business_mailing": {"type": "Point", "coordinates": [-98.22, 30.75]},
        }
        score = score_record(record, config)
        # 75 + 10 + 5 = 90
        assert score == 90

    def test_ac_technician_secondary_no_phone(self, config):
        record = {
            "license_type": "A/C Technician",
            "business_county": "BELL",
            "business_telephone": "",
            "owner_telephone": "",
            "business_mailing": None,
        }
        score = score_record(record, config)
        # 25 + 0 = 25
        assert score == 25

    def test_phone_falls_back_to_owner(self, config):
        record = {
            "license_type": "Electrical Contractor",
            "business_county": "BASTROP",
            "business_telephone": "",
            "owner_telephone": "5125554444",
            "business_mailing": None,
        }
        score = score_record(record, config)
        # 100 + 10 (owner phone counts) = 110
        assert score == 110

    def test_unknown_license_type(self, config):
        record = {
            "license_type": "Unknown Type",
            "business_county": "TRAVIS",
            "business_telephone": "5551234567",
            "business_mailing": None,
        }
        score = score_record(record, config)
        # 0 (unknown base) + 10 (phone) + 15 (primary) = 25
        assert score == 25


class TestScoreAndSort:
    def test_sorted_descending(self, sample_records):
        scored = score_and_sort(sample_records)
        scores = [r["_score"] for r in scored]
        assert scores == sorted(scores, reverse=True)

    def test_all_records_scored(self, sample_records):
        scored = score_and_sort(sample_records)
        assert len(scored) == len(sample_records)
        assert all("_score" in r for r in scored)

    def test_highest_is_electrical_contractor_primary(self, sample_records):
        scored = score_and_sort(sample_records)
        # First record should be the EC in Travis with phone and geo (score 130)
        assert scored[0]["license_number"] == "19901"
        assert scored[0]["_score"] == 130


class TestFormatPhone:
    def test_10_digit(self):
        assert format_phone("5126528463") == "(512) 652-8463"

    def test_11_digit_with_1(self):
        assert format_phone("15126528463") == "(512) 652-8463"

    def test_already_formatted(self):
        assert format_phone("(512) 652-8463") == "(512) 652-8463"

    def test_empty_string(self):
        assert format_phone("") == ""

    def test_short_number(self):
        assert format_phone("12345") == "12345"
