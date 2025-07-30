#!/usr/bin/env python3
import json
import pandas as pd
from playwright.sync_api import sync_playwright

def main():
    # Load cookies
    with open('cookies.json') as f:
        cookies = json.load(f)
    # Start Playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        # Navigate to JCtrans membership list
        page.goto("https://www.jctrans.com/en/membership/list/0-JC%20Elite,GCP?years=0&page=1", timeout=60000)
        page.wait_for_selector('table')
        # Extract table data
        rows = page.query_selector_all('table tbody tr')
        headers = [th.inner_text().strip() for th in page.query_selector_all('table thead th')]
        data = []
        for row in rows:
            data.append([td.inner_text().strip() for td in row.query_selector_all('td')])
        # Save to Excel
        df = pd.DataFrame(data, columns=headers)
        df.to_excel('output/contracts_page_1.xlsx', index=False)
        browser.close()

if __name__ == '__main__':
    main()
