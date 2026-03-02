"""
streamyard_uploader.py

Uploads local files to the Streamyard Spellbreakers studio.
Images go to Overlays, videos go to Video clips.

Usage:
    from streamyard_uploader import upload_assets

    upload_assets([
        '/path/to/sponsor-image.jpg',
        '/path/to/ad-video.mp4',
        '/path/to/another-image.png',
    ])
"""

import os
import json
import threading
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

STUDIO_URL    = os.environ['STUDIO_URL']
SESSION_FILE  = 'streamyard_session.json'

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

# ── Helpers ───────────────────────────────────────────────────────────────────

def classify_file(file_path: str) -> str:
    """Return 'overlay' or 'video' based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'overlay'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    raise ValueError(f"Unrecognized file type: {ext} ({file_path})")


def heartbeat(stop_event: threading.Event, filename: str):
    """Print progress dots while waiting for a long upload."""
    import time
    elapsed = 0
    while not stop_event.is_set():
        time.sleep(15)
        elapsed += 15
        print(f"  [{filename}] still uploading... {elapsed}s elapsed", flush=True)


def wait_for_upload(page, file_path: str, timeout_ms: int = 600_000):
    """
    Poll until the uploaded file's tile appears in the media grid.
    Uses first 20 chars of filename stem to handle Streamyard's truncation.
    """
    filename      = os.path.basename(file_path)
    filename_stem = os.path.splitext(filename)[0]
    search_text   = filename_stem[:20]

    stop = threading.Event()
    t = threading.Thread(target=heartbeat, args=(stop, filename), daemon=True)
    t.start()

    try:
        page.wait_for_selector(f'text={search_text}', timeout=timeout_ms)
        print(f"  ✓ Upload confirmed: {filename}", flush=True)
    finally:
        stop.set()
        t.join()


# ── Core upload logic ─────────────────────────────────────────────────────────

def upload_single(page, file_path: str, asset_type: str):
    """Upload one file to the appropriate section in the open studio page."""
    filename = os.path.basename(file_path)
    print(f"\n→ Uploading [{asset_type}]: {filename}", flush=True)

    # Ensure Media assets panel is open
    page.get_by_text('Media assets').click()
    page.wait_for_timeout(800)

    # Expand the correct section
    if asset_type == 'overlay':
        page.get_by_text('Overlay', exact=True).click()
    else:
        page.get_by_text('Video clips', exact=True).click()
    page.wait_for_timeout(500)

    # Click More [+], then Add file inside the modal
    page.get_by_role('button', name='More').last.click()
    page.wait_for_timeout(500)

    with page.expect_file_chooser() as fc_info:
        page.get_by_role('button', name='Add file').click()

    fc_info.value.set_files(file_path)

    # Wait for tile to appear confirming upload complete
    wait_for_upload(page, file_path)


# ── Public API ────────────────────────────────────────────────────────────────

def upload_assets(file_paths: list[str], headless: bool = False):
    """
    Upload a list of local files to the Spellbreakers studio.

    Args:
        file_paths: List of absolute paths to image/video files.
        headless:   Set True once you trust it; False keeps browser visible.
    """
    if not file_paths:
        print("No files to upload.")
        return

    # Validate all files exist and are classifiable before opening the browser
    classified = []
    for path in file_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        classified.append((path, classify_file(path)))

    print(f"Uploading {len(classified)} file(s) to Streamyard...")

    with open(SESSION_FILE) as f:
        cookies = json.load(f)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_cookies(cookies)

        page = context.new_page()
        page.goto(STUDIO_URL)
        page.wait_for_load_state('networkidle')

        for file_path, asset_type in classified:
            upload_single(page, file_path, asset_type)

        browser.close()

    print(f"\n✓ All uploads complete.")


# ── CLI usage ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python streamyard_uploader.py file1.jpg file2.mp4 ...")
        sys.exit(1)

    upload_assets(sys.argv[1:])