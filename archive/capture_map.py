"""平面図マップをPNG画像として保存"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
from pathlib import Path

page_name = sys.argv[1] if len(sys.argv) > 1 else "layout_real"
OUT = Path(__file__).parent / f"{page_name}.png"
URL = f"http://localhost:5000/static/{page_name}.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1180, "height": 980}, device_scale_factor=2)
    page.goto(URL)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(OUT), full_page=True)
    browser.close()
print(f"保存完了: {OUT}")
