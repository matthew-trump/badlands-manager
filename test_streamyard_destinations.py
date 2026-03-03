"""
test_streamyard_destinations.py

Logs into Streamyard using a saved session, prints the list of Destinations,
and checks each one for RTMP status by two criteria:
  1. Name contains 'RTMP' (case-insensitive)
  2. The three-dots menu contains an 'Edit' option
"""

import json
from playwright.sync_api import sync_playwright

SESSION_FILE = 'streamyard_session.json'
HOME_URL     = 'https://streamyard.com'

PLATFORMS = {
    'YouTube', 'YouTube and YouTube Shorts', 'Facebook', 'LinkedIn',
    'Twitch', 'Twitter', 'Rumble', 'Rumble Account', 'Other platforms',
    'Periscope', 'Kick', 'TikTok',
}

with open(SESSION_FILE) as f:
    cookies = json.load(f)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    context.add_cookies(cookies)

    page = context.new_page()
    print("Navigating to Streamyard...")
    page.goto(HOME_URL)
    page.wait_for_load_state('domcontentloaded')
    page.wait_for_timeout(3000)

    page.get_by_text('Destinations', exact=True).first.click()
    page.wait_for_timeout(3000)

    # Find destination cards: li elements that contain a known platform string
    all_lis = page.locator('li').all()
    cards = []
    for li in all_lis:
        text = li.inner_text()
        for platform in PLATFORMS:
            if platform in text:
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                name = next((l for l in lines if l != platform and len(l) > 1), None)
                if name:
                    cards.append((name, platform, li))
                break

    print(f"\nFound {len(cards)} destination(s):\n")

    for name, platform, card in cards:
        name_rtmp = 'rtmp' in name.lower()

        # Hover to reveal the three-dots button, then click it
        card.hover()
        page.wait_for_timeout(500)

        dots_button = card.locator('button').last
        dots_button.click()
        page.wait_for_timeout(500)

        # Check if an 'Edit' option appears in the resulting menu/popup
        edit_locator = page.get_by_role('menuitem', name='Edit')
        if not edit_locator.count():
            edit_locator = page.get_by_text('Edit', exact=True)
        edit_rtmp = edit_locator.count() > 0

        rtmp_url = None
        stream_key = None

        if edit_rtmp:
            edit_locator.first.click()
            page.wait_for_timeout(2000)

            # Read RTMP server URL and stream key without modifying them
            rtmp_url_input = page.get_by_label('RTMP server URL', exact=False)
            if not rtmp_url_input.count():
                rtmp_url_input = page.locator('input[name*="rtmp" i], input[placeholder*="rtmp" i]')
            if rtmp_url_input.count():
                rtmp_url = rtmp_url_input.first.input_value()

            stream_key_input = page.get_by_label('Stream key', exact=False)
            if not stream_key_input.count():
                stream_key_input = page.locator('input[name*="key" i], input[placeholder*="key" i]')
            if stream_key_input.count():
                stream_key = stream_key_input.first.input_value()

            # Back out without saving — try visible Cancel button, then Escape, then go_back
            cancel = page.locator('button:visible', has_text='Cancel')
            if cancel.count():
                cancel.first.click()
            else:
                page.keyboard.press('Escape')
                page.wait_for_timeout(500)
                # If still on the edit form, navigate back
                if rtmp_url_input.count():
                    page.go_back()
            page.wait_for_timeout(1500)
        else:
            # Close the menu without doing anything
            page.keyboard.press('Escape')

        page.wait_for_timeout(300)

        print(f"  {name} — {platform}")
        print(f"    RTMP by name:       {name_rtmp}")
        print(f"    RTMP by Edit menu:  {edit_rtmp}")
        if edit_rtmp:
            print(f"    RTMP server URL:    {rtmp_url}")
            print(f"    Stream key:         {stream_key}")

    browser.close()
