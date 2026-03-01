import os
import re
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import requests

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'
FOLDER_ID = os.environ['FOLDER_ID']

# Date pattern: m.DD.YY at the start of the filename
DATE_PATTERN = re.compile(r'^(\d{1,2})\.(\d{2})\.(\d{2})\s+')

def parse_filename_date(name: str) -> datetime | None:
    m = DATE_PATTERN.match(name)
    if not m:
        return None
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(2000 + year, month, day)

def get_next_spreadsheet() -> tuple[str, str, str] | None:
    """Returns (file_id, filename, mime_type) for the next upcoming show."""
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    # List xlsx files in the folder
    query = (
        f"'{FOLDER_ID}' in parents and trashed = false and "
        "(mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' "
        " or mimeType='application/vnd.google-apps.spreadsheet')"
    )
    results = service.files().list(q=query, fields='files(id, name, mimeType)').execute()
    files = results.get('files', [])

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Parse dates and keep only future/today files
    candidates = []
    for f in files:
        date = parse_filename_date(f['name'])
        if date and date >= today:
            candidates.append((date, f['id'], f['name'], f['mimeType']))

    if not candidates:
        print("No upcoming spreadsheets found.")
        return None

    # Pick the earliest upcoming date
    candidates.sort(key=lambda x: x[0])
    _, file_id, file_name, mime_type = candidates[0]
    return file_id, file_name, mime_type

def download_spreadsheet(file_id: str, file_name: str, mime_type: str) -> str:
    """Download the file and return the local path."""
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    # If it's a native Google Sheet, export as xlsx; otherwise download directly
    if mime_type == 'application/vnd.google-apps.spreadsheet':
        export_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        local_name = file_name.rstrip('.xlsx') + '.xlsx' if not file_name.endswith('.xlsx') else file_name
    else:
        request = service.files().get_media(fileId=file_id)
        local_name = file_name

    with open(local_name, 'wb') as f:
        f.write(request.execute())

    print(f"Downloaded: {local_name}")
    return local_name

if __name__ == '__main__':
    result = get_next_spreadsheet()
    if result:
        file_id, file_name, mime_type = result
        print(f"Next show file: {file_name}")
        path = download_spreadsheet(file_id, file_name, mime_type)
        
        # Now load it with openpyxl or pandas
        import pandas as pd
        df = pd.read_excel(path)
        print(df.head())