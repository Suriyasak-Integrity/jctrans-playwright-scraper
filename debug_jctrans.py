#!/usr/bin/env python3
"""
JCTrans Debug Script
Simple script to inspect the JCTrans website structure and find the right selectors.
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import re

async def debug_jctrans_page():
    """Debug the JCTrans listing page to understand its structure."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see the browser
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        # Load cookies if available
        try:
            cookies_path = Path("cookies.json")
            if cookies_path.exists():
                with open(cookies_path) as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                print("✅ Loaded cookies from cookies.json")
        except Exception as e:
            print(f"⚠️ Could not load cookies: {e}")
        
        page = await context.new_page()
        
        # Navigate to the JCTrans listing page
        url = "https://www.jctrans.com/en/membership/list/0-JC%20Elite,GCP?years=0&page=1"
        print(f"🌐 Navigating to: {url}")
        
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=30000)
        
        # Get page title and URL
        title = await page.title()
        current_url = page.url
        print(f"📄 Page Title: {title}")
        print(f"🔗 Current URL: {current_url}")
        
        # Save page content for analysis
        content = await page.content()
        with open("debug/page_content.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("💾 Saved page content to debug/page_content.html")
        
        # Take a screenshot
        await page.screenshot(path="debug/page_screenshot.png", full_page=True)
        print("📸 Saved screenshot to debug/page_screenshot.png")
        
        # Test different selectors to find company links
        selectors_to_test = [
            'a[href*="/company/"]',
            'a[href*="/profile/"]', 
            'a[href*="/member/"]',
            'table tbody tr td a',
            'tbody tr td a[href]',
            '.company-list a',
            '.member-list a',
            'a[href]',  # All links
        ]
        
        print("\n🔍 Testing selectors for company links:")
        print("=" * 50)
        
        all_links_info = []
        
        for selector in selectors_to_test:
            try:
                elements = await page.query_selector_all(selector)
                print(f"Selector '{selector}': Found {len(elements)} elements")
                
                if elements:
                    for i, element in enumerate(elements[:5]):  # Show first 5
                        href = await element.get_attribute('href')
                        text = await element.inner_text()
                        title_attr = await element.get_attribute('title')
                        
                        if href:
                            # Clean up text
                            text = text.strip().replace('\n', ' ')[:100] if text else ""
                            
                            link_info = {
                                'selector': selector,
                                'href': href,
                                'text': text,
                                'title': title_attr or ""
                            }
                            all_links_info.append(link_info)
                            
                            print(f"  [{i+1}] {href}")
                            print(f"      Text: {text}")
                            if title_attr:
                                print(f"      Title: {title_attr}")
                            print()
                            
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
        
        # Save all link information
        with open("debug/all_links.json", "w", encoding="utf-8") as f:
            json.dump(all_links_info, f, indent=2, ensure_ascii=False)
        print("💾 Saved all link information to debug/all_links.json")
        
        # Look for specific patterns in the page
        page_text = await page.inner_text('body')
        
        # Find company names
        company_patterns = [
            r'\b[A-Z][a-zA-Z\s&]+(?:Ltd|Limited|Inc|Corp|Company|Co\.|Group|International|Logistics|Shipping|Express)\b',
            r'\b[A-Z][a-zA-Z\s&]{5,50}(?=\s*(?:Contact|Email|Phone|Address))',
        ]
        
        print("\n🏢 Potential company names found:")
        print("=" * 50)
        
        companies_found = set()
        for pattern in company_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches[:10]:  # Show first 10
                match = match.strip()
                if len(match) > 5 and match not in companies_found:
                    companies_found.add(match)
                    print(f"  • {match}")
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, page_text)
        
        print(f"\n📧 Email addresses found: {len(emails)}")
        for email in emails[:5]:  # Show first 5
            print(f"  • {email}")
        
        # Look for phone numbers
        phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
        phones = re.findall(phone_pattern, page_text)
        
        print(f"\n📞 Phone numbers found: {len(phones)}")
        for phone in phones[:5]:  # Show first 5
            print(f"  • {phone.strip()}")
        
        # Check if we need to handle pagination or login
        pagination_selectors = ['a[href*="page="]', '.pagination', '.next', '.prev']
        login_selectors = ['a[href*="login"]', '.login', 'input[type="password"]']
        
        print("\n🔄 Pagination elements:")
        for selector in pagination_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"  Found {len(elements)} elements for '{selector}'")
        
        print("\n🔐 Login elements:")
        for selector in login_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"  Found {len(elements)} elements for '{selector}'")
        
        # Wait a bit before closing
        print("\n⏳ Waiting 5 seconds before closing...")
        await asyncio.sleep(5)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_jctrans_page())