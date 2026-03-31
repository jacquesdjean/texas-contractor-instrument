<div align="center">

# TDLR License Monitor

**Automated detection and scoring of newly licensed contractors in Central Texas**

[![CI](https://github.com/jacquesdjean/texas-contractor-instrument/actions/workflows/ci.yml/badge.svg)](https://github.com/jacquesdjean/texas-contractor-instrument/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Conventional Commits](https://img.shields.io/badge/commits-conventional-fe5196.svg)](https://www.conventionalcommits.org)

[Quick Start](#quick-start) | [Documentation](#how-it-works) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md)

</div>

---

## Overview

TDLR License Monitor is an automated pipeline that detects **newly licensed**
contractors in Central Texas by monitoring government datasets from the Texas
Department of Licensing and Regulation (TDLR) and the Texas State Board of
Plumbing Examiners (TSBPE).

Each week, it queries the Texas Open Data Portal via the Socrata SODA API,
diffs snapshots to identify new license numbers, scores them by recruitment
value, and pushes results to Google Sheets with optional Slack and email
notifications.

### Key Features

- **Automated weekly scanning** via GitHub Actions (Mondays 7:00 AM CT)
- **New license detection** through snapshot diffing — no issue date required
- **Reinstated license tracking** to catch returning contractors
- **Recruitment scoring** (0-130 scale) based on license type, location, and contact info
- **Google Sheets integration** with structured weekly summary and individual lead tabs
- **Slack and email notifications** for high-priority licenses (score >= 90)
- **Fully configurable** via YAML — territory, license types, scoring weights

## Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Data Sources](#data-sources)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Scoring System](#scoring-system)
- [Notifications](#notifications)
- [Deployment](#deployment)
- [Local Development](#local-development)
- [Testing](#testing)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/jacquesdjean/texas-contractor-instrument.git
cd texas-contractor-instrument
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your API tokens and credentials

# 3. Run the monitor
python -m src.main
```

> **Note:** The first run creates a baseline snapshot. New licenses are detected
> starting from the second run.

## How It Works

The TDLR dataset does **not** include a license issue date — only expiration
dates. To detect newly issued licenses, this tool uses weekly snapshot diffing:

```
1. FETCH      Pulls the full filtered dataset from TDLR/TSBPE APIs
                    |
2. DIFF       Compares current license numbers against last week's snapshot
                    |
3. DETECT     Flags licenses present now but absent last week as "new"
              Flags reappearing licenses as "reinstated"
                    |
4. SCORE      Ranks each new license by recruitment value (0-130)
                    |
5. OUTPUT     Pushes results to Google Sheets
              Sends Slack/email alerts for high-priority leads
                    |
6. PERSIST    Commits updated snapshots back to the repository
```

A cumulative historical file tracks all license numbers ever seen to prevent
duplicate detection of reinstated licenses.

## Data Sources

| Agency   | Dataset ID  | Endpoint                                 | License Types                       |
|----------|-------------|------------------------------------------|-------------------------------------|
| **TDLR** | `7358-krk7` | `data.texas.gov/resource/7358-krk7.json` | Electrical, HVAC, Water Well, Appliance |
| **TSBPE**| `qced-zkby` | `data.texas.gov/resource/qced-zkby.json` | Plumbing (optional)                 |

Both use the Socrata SODA API. An app token is optional but recommended to avoid
throttling.

## Architecture

```
texas-contractor-instrument/
|
├── src/                            Source Code
│   ├── main.py                     Pipeline orchestrator
│   ├── scraper.py                  TDLR Socrata API client
│   ├── tsbpe_scraper.py            TSBPE plumbing license scraper
│   ├── differ.py                   Snapshot diffing + reinstated detection
│   ├── scorer.py                   Recruitment value scoring engine
│   ├── sheets_output.py            Google Sheets API integration
│   └── notifications.py            Slack webhook + SMTP email alerts
│
├── config/                         Configuration (YAML)
│   ├── territory.yml               County definitions (primary + secondary)
│   ├── license_types.yml           License type mappings for TDLR/TSBPE
│   └── scoring.yml                 Base scores and bonus weights
│
├── tests/                          Test Suite (44 tests)
│   ├── test_differ.py              Snapshot diffing tests
│   ├── test_scorer.py              Scoring logic tests
│   ├── test_notifications.py       Notification delivery tests
│   └── fixtures/                   Sample API response data
│
├── data/                           Runtime State (committed weekly by CI)
│   ├── previous_snapshot.json      Current week's license numbers
│   ├── historical_licenses.json    All-time cumulative license set
│   └── run_log.json                Last execution metadata
│
├── .github/workflows/              CI/CD Automation
│   ├── ci.yml                      Tests, linting, coverage (matrix: 3.11, 3.12)
│   ├── weekly-scan.yml             Scheduled Monday scan + snapshot commit
│   ├── release.yml                 Build + GitHub Release on version tags
│   └── codeql.yml                  Security analysis
│
├── pyproject.toml                  Project metadata, dependencies, tool config
├── Makefile                        Developer task runner
├── CONTRIBUTING.md                 Contribution guidelines
├── CHANGELOG.md                    Release history
├── CODE_OF_CONDUCT.md              Community standards
├── SECURITY.md                     Vulnerability disclosure policy
└── LICENSE                         Apache License 2.0
```

### Module Data Flow

```
main.py
 ├── run_tdlr_pipeline()
 │   ├── scraper.fetch_licenses()          <-- TDLR Socrata API
 │   └── differ.diff_snapshots()           <-- previous_snapshot.json
 │
 ├── run_tsbpe_pipeline()                  (if ENABLE_TSBPE=1)
 │   ├── tsbpe_scraper.fetch_plumbing_licenses()
 │   └── differ.diff_snapshots()           <-- tsbpe_previous_snapshot.json
 │
 ├── scorer.score_and_sort()               <-- Combined new licenses
 ├── sheets_output.push_to_sheets()        --> Google Sheets API
 ├── notifications.notify()                --> Slack / Email
 └── update_run_log()                      --> run_log.json
```

## Configuration

All business logic is configured via YAML files in `config/`. No code changes
are needed to customize behavior.

### Territory (`config/territory.yml`)

Defines the geographic scope of license monitoring.

```yaml
primary_counties:    # +15 scoring bonus
  - Travis
  - Williamson
  - Hays

secondary_counties:  # No bonus, still monitored
  - Burnet
  - Bastrop
  - Bell
  - Caldwell
  - Blanco
  - Llano
  - Lampasas
  - Lee
  - Milam
```

### License Types (`config/license_types.yml`)

Maps API license type strings to categories. Use exact values from the
TDLR/TSBPE `license_type` field.

### Scoring Weights (`config/scoring.yml`)

Defines base scores per license type and bonus point values. See
[Scoring System](#scoring-system) for the full breakdown.

## Scoring System

Each new license is scored on a 0-130 scale based on recruitment value.

### Base Scores by License Type

#### TDLR

| Type                                | Category    | Base Score |
|-------------------------------------|-------------|------------|
| Electrical Contractor (EC)          | Electrical  | 100        |
| A/C Contractor                      | HVAC        | 90         |
| Appliance Installation Contractor   | Appliance   | 80         |
| Water Well Driller/Pump Installer   | Water       | 75         |
| Master Electrician                  | Electrical  | 60         |
| Journeyman Electrician              | Electrical  | 30         |
| A/C Technician                      | HVAC        | 25         |

#### TSBPE (Optional)

| Type                                | Category    | Base Score |
|-------------------------------------|-------------|------------|
| Master Plumber                      | Plumbing    | 85         |
| Residential Utilities Installer     | Plumbing    | 50         |
| Water Supply Protection Specialist  | Plumbing    | 45         |
| Journeyman Plumber                  | Plumbing    | 40         |
| Tradesman Plumber-Limited           | Plumbing    | 35         |
| Drain Cleaner                       | Plumbing    | 20         |
| Plumber's Apprentice                | Plumbing    | 15         |
| Drain Cleaner-Restricted            | Plumbing    | 15         |

### Bonus Points

| Bonus              | Points | Condition                                      |
|--------------------|--------|------------------------------------------------|
| Has phone number   | +10    | `business_telephone` or `owner_telephone` present |
| Primary county     | +15    | Travis, Williamson, or Hays                    |
| Has geocoordinates | +5     | `business_mailing` field present               |

**Maximum theoretical score: 130** (Electrical Contractor in a primary county
with phone and geocoordinates).

## Notifications

High-priority licenses (score >= 90) trigger optional notifications:

- **Slack** — Rich block messages via incoming webhook
- **Email** — SMTP digest with license details

Notifications are skipped gracefully when not configured. Configure via
environment variables (see [Deployment](#deployment)).

## Deployment

### GitHub Actions (Recommended)

The weekly scan runs automatically via GitHub Actions every Monday at 7:00 AM CT.

#### Required Secrets

| Secret                | Required | Description                                |
|-----------------------|----------|--------------------------------------------|
| `SOCRATA_APP_TOKEN`   | Optional | Socrata app token (avoids API throttling)  |
| `GOOGLE_SHEETS_CREDS` | Optional | Base64-encoded service account JSON        |
| `GOOGLE_SHEET_ID`     | Optional | Target Google Sheet ID                     |
| `SLACK_WEBHOOK_URL`   | Optional | Slack incoming webhook URL                 |
| `SMTP_HOST`           | Optional | SMTP server hostname                       |
| `SMTP_PORT`           | Optional | SMTP port (default: 587)                   |
| `SMTP_USER`           | Optional | SMTP username/email                        |
| `SMTP_PASS`           | Optional | SMTP password or app password              |
| `NOTIFICATION_EMAIL`  | Optional | Recipient email for alerts                 |
| `ENABLE_TSBPE`        | Optional | Set to `1` to enable TSBPE plumbing scraper|

#### Google Sheets Setup

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com/)
   with Google Sheets API access
2. Download the JSON key file
3. Base64-encode it: `base64 -w 0 service-account.json`
4. Add as `GOOGLE_SHEETS_CREDS` secret
5. Share your target Google Sheet with the service account email
6. Create two tabs: **New Licenses** and **Weekly Summary**

#### Manual Trigger

The weekly scan can also be triggered manually via the GitHub Actions
`workflow_dispatch` event.

## Local Development

### Prerequisites

- Python 3.11+ (3.12 also supported)
- make (optional but recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/jacquesdjean/texas-contractor-instrument.git
cd texas-contractor-instrument

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
make install
# Or: pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Available Make Targets

```
$ make help
clean           Remove build artifacts and caches
format          Auto-format code
format-check    Check code formatting without modifying files
help            Show this help message
install         Install package with dev dependencies
lint            Run linter checks
pre-commit      Run pre-commit hooks on all files
run             Run the TDLR License Monitor
test            Run the test suite
test-cov        Run tests with coverage report
```

## Testing

```bash
make test              # Run all 44 tests
make test-cov          # Run with coverage report
python -m pytest tests/test_differ.py -v   # Run specific test file
```

The test suite covers:

- **Snapshot diffing** — new, removed, and reinstated license detection
- **Scoring logic** — base scores, bonus calculations, phone formatting
- **Notifications** — Slack and email delivery for high-priority licenses

## FAQ

**Q: Why does the first run report zero new licenses?**
The first run creates a baseline snapshot of all existing licenses. New licenses
are detected by comparing against this baseline on subsequent runs.

**Q: How often does the monitor run?**
Weekly, every Monday at 7:00 AM Central Time via GitHub Actions. It can also be
triggered manually.

**Q: Can I add more counties?**
Yes. Edit `config/territory.yml` and add counties to either `primary_counties`
(with scoring bonus) or `secondary_counties`.

**Q: Is the TSBPE scraper enabled by default?**
No. Set `ENABLE_TSBPE=1` in your environment or GitHub Secrets to enable
plumbing license tracking.

**Q: What if the Socrata API is down?**
The scraper includes exponential backoff retry logic. If the API is
unresponsive after retries, the run will fail and can be retried via
`workflow_dispatch`.

**Q: Can I run this for other states?**
The architecture supports any Socrata-based state data portal. You would need to
update the dataset IDs, license types, and territory configuration.

## Known Limitations

- **No issue date** — TDLR does not publish license issue dates. Detection
  relies on weekly diffs, so licenses issued and revoked within the same week
  may be missed.
- **TSBPE verification** — The TSBPE endpoint (`qced-zkby`) needs verification
  against the live API. Field names may differ slightly from TDLR.
- **Geocoordinates** — Not all records include `business_mailing` coordinates.

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md)
for details on:

- Development setup
- Code style and commit conventions
- Pull request process
- Testing guidelines

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE)
file for details.

## Acknowledgments

- [Texas Open Data Portal](https://data.texas.gov/) for providing public
  license datasets
- [Socrata Open Data API](https://dev.socrata.com/) for the SODA query interface
- [Contributor Covenant](https://www.contributor-covenant.org/) for the
  Code of Conduct
