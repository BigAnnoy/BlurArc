"""
截取五种设计风格的 PNG
"""
from playwright.sync_api import sync_playwright
import os, time

html_path = os.path.abspath('f:/AI/Frame_Album/docs/landing-5-designs.html').replace('\\', '/')
url = f'file:///{html_path}'
out_dir = 'f:/AI/Frame_Album/docs/posters'

design_names = [
    'minimal-cards',
    'magazine-cover',
    'feature-grid',
    'story-narrative',
    'data-visualization',
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1080, 'height': 1440})
    page.goto(url, wait_until='networkidle')
    time.sleep(0.5)

    designs = page.locator('.promo')
    count = designs.count()

    for i in range(min(count, len(design_names))):
        name = design_names[i]
        design = designs.nth(i)
        out_path = f'{out_dir}/landing-{name}.png'
        design.screenshot(path=out_path)
        size_kb = os.path.getsize(out_path) / 1024
        print(f'OK: {name} -> {os.path.basename(out_path)} ({size_kb:.0f} KB)')

    browser.close()

print('Done: 5 designs captured')