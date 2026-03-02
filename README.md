# Badlands Manager

Pre-show preparation tool for Badlands Media live streams. Fetches the run sheet for the next upcoming show from Google Drive, validates it, downloads sponsor ad files, and prepares them for upload to Streamyard.

## How It Works

1. **Finds the next show** — scans a Google Drive folder for spreadsheets named with the pattern `m.DD.YY Show Name.xlsx` and picks the earliest upcoming date. Falls back to the most recent past file if none are found.
2. **Downloads the run sheet** — saves it to `runsheets/`, skipping if the local copy is already up to date.
3. **Validates the run sheet** — confirms the show name matches `SHOW_NAME` and the date in the sheet matches the filename.
4. **Parses the run sheet** — prints sponsors, background image status, and the ad schedule.
5. **Downloads sponsor files** — fetches each ad's linked video or image from Google Drive into `sponsor-downloads/`, skipping files that haven't changed since last download.
6. **Streamyard upload** *(separate script)* — `streamyard_uploader.py` uploads the downloaded files to the correct Streamyard studio, routing images to Overlays and videos to Video clips.

## Setup

### 1. Python environment

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Google Drive service account

- Create a service account in [Google Cloud Console](https://console.cloud.google.com/)
- Enable the **Google Drive API**
- Download the service account key and save it as `credentials.json` in the project root
- Share the run sheet folder with the service account email

### 3. Environment variables

Copy `.env-example` to `.env` and fill in your values:

```bash
cp .env-example .env
```

| Variable | Description |
|---|---|
| `FOLDER_ID` | Google Drive folder ID containing the run sheets (from the folder URL) |
| `SHOW_NAME` | Show name as it appears in cell A1 of the run sheet (e.g. `Spellbreakers`) |
| `STUDIO_URL` | Streamyard studio URL (e.g. `https://streamyard.com/your_studio_id`) |

### 4. Streamyard session

`streamyard_uploader.py` authenticates via saved browser cookies. Generate `streamyard_session.json` by logging into Streamyard with Playwright and saving the session. This file is gitignored and must not be committed.

## Run Sheet Format

The script expects the run sheet (`Run Sheet` tab) to follow this structure:

| Row | Content |
|---|---|
| 1 | Show name |
| 2 | Show date |
| 3 | *(blank)* |
| 4 | `Today's Sponsors` header |
| 5+ | Sponsor names (one per row, ended by a blank or long row) |
| ... | Background image note |
| ... | `Show Schedule` header |
| ... | Ad table with columns: Ad, Ad Type, Advertiser, Ad Link, Copy |

Spreadsheet filenames must follow the pattern `m.DD.YY Show Name.xlsx` (e.g. `3.06.26 Spellbreakers.xlsx`).

## Files

```
app.py                    # Main script
streamyard_uploader.py    # Streamyard upload tool (separate process)
credentials.json          # Google service account key (gitignored)
.env                      # Local environment variables (gitignored)
.env-example              # Example environment file
requirements.txt          # Python dependencies
runsheets/                # Downloaded run sheets (gitignored)
sponsor-downloads/        # Downloaded sponsor ad files (gitignored)
streamyard_session.json   # Streamyard auth cookies (gitignored)
```

## Usage

```bash
# Run the main prep script
source env/bin/activate
python app.py

# Upload downloaded files to Streamyard (separate step)
python streamyard_uploader.py
```
