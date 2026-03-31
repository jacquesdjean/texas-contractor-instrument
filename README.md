# TDLR Contractor License Monitor

A weekly scraper that detects **newly licensed** contractors in Central Texas by monitoring the Texas Department of Licensing and Regulation (TDLR) dataset. It queries the Texas Open Data Portal via the Socrata SODA API, diffs weekly snapshots to find new license numbers, scores them by recruitment value, and pushes results to Google Sheets.

## Data Source

- **Agency:** Texas Department of Licensing and Regulation (TDLR)
- **Portal:** [Texas Open Data Portal](https://data.texas.gov)
- **Dataset:** `7358-krk7` — TDLR License Data
- **API:** Socrata SODA API (`https://data.texas.gov/resource/7358-krk7.json`)
- **Authentication:** Optional Socrata app token (avoids throttling)

## How "New License" Detection Works

The TDLR dataset does **not** include a license issue date — only `license_expiration_date_mmddccyy`. To detect newly issued licenses, this tool:

1. Fetches the full filtered dataset each week (all target license types in target counties)
2. Compares current license numbers against the previous week's snapshot
3. Any license number present now but absent last week is flagged as "new"
4. The updated snapshot is committed back to the repo

On the **first run**, all existing licenses are saved as the baseline — nothing is reported as new. New licenses are detected starting from the second run.

## License Types Tracked

| Type | Category | Priority |
|------|----------|----------|
| Electrical Contractor (EC) | Electrical | Highest |
| Master Electrician | Electrical | High |
| Journeyman Electrician | Electrical | Medium |
| A/C Contractor | HVAC | High |
| A/C Technician | HVAC | Medium |
| Water Well Driller/Pump Installer | Water | High |
| Appliance Installation Contractor | Appliance | High |

## Territory

Central Texas counties: Travis, Williamson, Hays, Burnet, Bastrop, Bell, Caldwell, Blanco, Llano, Lampasas, Lee, Milam

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

| Secret | Description |
|--------|-------------|
| `SOCRATA_APP_TOKEN` | Optional — Socrata app token to avoid API throttling |
| `GOOGLE_SHEETS_CREDS` | Base64-encoded service account JSON |
| `GOOGLE_SHEET_ID` | ID of the target Google Sheet |

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

Edit `config/license_types.yml` — use exact strings from the TDLR API `license_type` field.

### Adjust scoring weights

Edit `config/scoring.yml` — modify base scores per license type or bonus point values.

## Automated Schedule

The GitHub Actions workflow (`.github/workflows/weekly-scan.yml`) runs every **Monday at 7:00 AM Central Time**. It can also be triggered manually via `workflow_dispatch`.

## Known Limitations

- **No issue date:** TDLR does not publish license issue dates. Detection relies on weekly snapshot diffs, so licenses issued and revoked within the same week may be missed.
- **No plumbing:** Texas plumbing is regulated by the Texas State Board of Plumbing Examiners (TSBPE), a separate agency with its own license lookup at `tsbpe.texas.gov`. Not included in v1.
- **First run:** The initial run creates a baseline only — no new licenses are reported until the second run.
- **Geocoordinates:** Not all records include `business_mailing` coordinates.

## Future Enhancements

- Add TSBPE plumbing license scraper
- Email/Slack notifications for high-priority new licenses
- Territory heatmap visualization
- Historical trend analysis dashboard
