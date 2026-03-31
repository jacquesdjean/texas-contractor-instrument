# TDLR Contractor License Monitor

A weekly scraper that detects **newly licensed** contractors in Central Texas by monitoring the Texas Department of Licensing and Regulation (TDLR) and Texas State Board of Plumbing Examiners (TSBPE) datasets. It queries the Texas Open Data Portal via the Socrata SODA API, diffs weekly snapshots to find new license numbers, scores them by recruitment value, and pushes results to Google Sheets with optional Slack/email notifications.

## Data Sources

| Agency | Dataset | Endpoint | License Types |
|--------|---------|----------|---------------|
| **TDLR** | `7358-krk7` | `data.texas.gov/resource/7358-krk7.json` | Electrical, HVAC, Water Well, Appliance |
| **TSBPE** | `qced-zkby` | `data.texas.gov/resource/qced-zkby.json` | Plumbing (optional, enable via env var) |

Both use the Socrata SODA API. Authentication is optional but recommended (app token avoids throttling).

## How "New License" Detection Works

The TDLR dataset does **not** include a license issue date — only `license_expiration_date_mmddccyy`. To detect newly issued licenses, this tool:

1. Fetches the full filtered dataset each week (all target license types in target counties)
2. Compares current license numbers against the previous week's snapshot
3. Any license number present now but absent last week is flagged as "new"
4. Licenses that reappear after previously disappearing are flagged as "reinstated"
5. A cumulative historical file tracks all license numbers ever seen
6. The updated snapshots are committed back to the repo

On the **first run**, all existing licenses are saved as the baseline — nothing is reported as new. New licenses are detected starting from the second run.

## License Types Tracked

### TDLR

| Type | Category | Base Score |
|------|----------|------------|
| Electrical Contractor (EC) | Electrical | 100 |
| A/C Contractor | HVAC | 90 |
| Appliance Installation Contractor | Appliance | 80 |
| Water Well Driller/Pump Installer | Water | 75 |
| Master Electrician | Electrical | 60 |
| Journeyman Electrician | Electrical | 30 |
| A/C Technician | HVAC | 25 |

### TSBPE (optional)

| Type | Category | Base Score |
|------|----------|------------|
| Master Plumber | Plumbing | 85 |
| Residential Utilities Installer | Plumbing | 50 |
| Water Supply Protection Specialist | Plumbing | 45 |
| Journeyman Plumber | Plumbing | 40 |
| Tradesman Plumber-Limited | Plumbing | 35 |
| Drain Cleaner | Plumbing | 20 |
| Plumber's Apprentice | Plumbing | 15 |
| Drain Cleaner-Restricted | Plumbing | 15 |

## Scoring

Final score = base license type score + applicable bonuses:

| Bonus | Points | Condition |
|-------|--------|-----------|
| Has phone number | +10 | `business_telephone` or `owner_telephone` present |
| Primary county | +15 | Travis, Williamson, or Hays |
| Has geocoordinates | +5 | `business_mailing` field present |

Max theoretical score: **130** (Electrical Contractor in primary county with phone and geocoordinates).

## Territory

Central Texas counties: Travis, Williamson, Hays, Burnet, Bastrop, Bell, Caldwell, Blanco, Llano, Lampasas, Lee, Milam

## Notifications

High-priority licenses (score >= 90) trigger optional notifications:

- **Slack:** Rich block messages via incoming webhook
- **Email:** SMTP digest with license details

Notifications are skipped gracefully when not configured.

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-org/tdlr-license-monitor.git
cd tdlr-license-monitor
pip install -r requirements.txt
```

### 2. Create a Google Sheets service account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a service account with Google Sheets API access
3. Download the JSON key file
4. Base64-encode it: `base64 -w 0 service-account.json`
5. Share your target Google Sheet with the service account email

### 3. Set GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `SOCRATA_APP_TOKEN` | Optional | Socrata app token to avoid API throttling |
| `GOOGLE_SHEETS_CREDS` | Optional | Base64-encoded service account JSON |
| `GOOGLE_SHEET_ID` | Optional | ID of the target Google Sheet |
| `SLACK_WEBHOOK_URL` | Optional | Slack incoming webhook URL |
| `SMTP_HOST` | Optional | SMTP server hostname |
| `SMTP_PORT` | Optional | SMTP port (default: 587) |
| `SMTP_USER` | Optional | SMTP username/email |
| `SMTP_PASS` | Optional | SMTP password or app password |
| `NOTIFICATION_EMAIL` | Optional | Recipient email for alerts |
| `ENABLE_TSBPE` | Optional | Set to `1` to enable TSBPE plumbing scraper |

### 4. Prepare the Google Sheet

Create a Google Sheet with two tabs:
- **New Licenses** — individual new license rows (appended weekly)
- **Weekly Summary** — one row per week with counts by type

## Local Run

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your values

python -m src.main
```

## Configuration

### Add/remove counties

Edit `config/territory.yml` — add counties to `primary_counties` (bonus scoring) or `secondary_counties`.

### Add/remove license types

Edit `config/license_types.yml` — use exact strings from the TDLR/TSBPE API `license_type` field.

### Adjust scoring weights

Edit `config/scoring.yml` — modify base scores per license type or bonus point values.

## CI/CD

### Automated Weekly Scan

The GitHub Actions workflow (`.github/workflows/weekly-scan.yml`) runs every **Monday at 7:00 AM Central Time**. It can also be triggered manually via `workflow_dispatch`.

### CI Pipeline

The CI workflow (`.github/workflows/ci.yml`) runs on all PRs and pushes to `main`/`master`:
- Runs the full test suite with pytest
- Validates Python syntax across all modules
- Enables auto-merge for PRs when tests pass

## Architecture

```
├── src/
│   ├── scraper.py          # TDLR Socrata API client
│   ├── tsbpe_scraper.py    # TSBPE plumbing license scraper
│   ├── differ.py           # Snapshot diffing + reinstated detection
│   ├── scorer.py           # Recruitment value scoring
│   ├── sheets_output.py    # Google Sheets integration
│   ├── notifications.py    # Slack + email alerts
│   └── main.py             # Orchestrator
├── config/                 # YAML configs for territory, types, scoring
├── data/                   # Snapshots + historical tracking (committed weekly)
├── tests/                  # Unit tests (44 tests)
└── .github/workflows/      # CI + weekly scan automation
```

## Known Limitations

- **No issue date:** TDLR does not publish license issue dates. Detection relies on weekly snapshot diffs, so licenses issued and revoked within the same week may be missed.
- **TSBPE dataset:** The TSBPE endpoint (`qced-zkby`) needs verification against the live API — field names may differ slightly from TDLR. Enable with `ENABLE_TSBPE=1` after confirming the endpoint.
- **First run:** The initial run creates a baseline only — no new licenses are reported until the second run.
- **Geocoordinates:** Not all records include `business_mailing` coordinates.

## Future Enhancements

- Territory heatmap visualization
- Historical trend analysis dashboard
- CRM integration webhooks
- Multi-state expansion (other Socrata-based state portals)
