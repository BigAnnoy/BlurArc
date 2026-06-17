from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)
    page.screenshot(path='f:/AI/Frame_Album/header-shot.png', clip={'x': 0, 'y': 0, 'width': 400, 'height': 60})
    box = page.locator('header').bounding_box()
    print('header box:', box)
    logo = page.locator('header svg').first
    lbox = logo.bounding_box()
    print('logo box:', lbox)
    print('logo visible:', logo.is_visible())
    browser.close()
