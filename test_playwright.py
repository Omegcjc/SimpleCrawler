# 测试脚本 test_playwright.py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False， channel = "chrome") # 使用本地Chrome
    page = browser.new_page()
    page.goto("https://www.baidu.com")
    print(page.title())
    browser.close()
