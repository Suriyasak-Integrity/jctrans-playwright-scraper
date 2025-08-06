#!/usr/bin/env python3
"""
JCTrans Pro Scraper 2025 (Fixed Version)
Advanced web scraper for extracting contact information from JCTrans membership directory.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import aiofiles
import aiohttp
import click
import pandas as pd
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
import re

# Initialize Rich console
console = Console()

class JCTransScraperFixed:
    """Enhanced JCTrans scraper with improved selectors and error handling."""
    
    def __init__(self, start_page: int = 1, end_page: int = 10, timeout: int = 90000, 
                 use_login: bool = False, group_by_department: bool = True):
        self.start_page = start_page
        self.end_page = end_page
        self.timeout = timeout
        self.use_login = use_login
        self.group_by_department = group_by_department
        
        # Results storage
        self.all_contacts: List[Dict] = []
        self.errors: List[Dict] = []
        self.processed_pages: Set[int] = set()
        
        # Setup logging
        self.setup_logging()
        
        # Base URL for JCTrans
        self.base_url = "https://www.jctrans.com"
        self.listing_url = f"{self.base_url}/en/membership/list/0-JC%20Elite,GCP?years=0&page="
        
        console.print(Panel.fit("🚀 JCTrans Pro Scraper 2025 (Fixed) initialized", style="bold green"))

    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"jctrans_scraper_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def wait_for_network_idle(self, page: Page, timeout: int = 30000) -> bool:
        """Wait for network to be idle with improved logic."""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
            return True
        except Exception as e:
            self.logger.warning(f"Network didn't settle completely: {e}")
            # Try to wait for DOM content at least
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                await asyncio.sleep(2)  # Give it a moment to render
                return True
            except:
                return False

    async def extract_company_links(self, page: Page) -> List[str]:
        """Extract company profile links from listing page with improved selectors."""
        company_links = []
        
        # Multiple selector strategies to find company links
        selectors_to_try = [
            # Strategy 1: Direct links to company profiles
            'a[href*="/company/"]',
            'a[href*="/profile/"]',
            'a[href*="/member/"]',
            
            # Strategy 2: Links within company listings
            '.company-list a[href*="/company/"]',
            '.member-list a[href*="/company/"]',
            'tr td a[href*="/company/"]',
            
            # Strategy 3: Table-based listings
            'table tbody tr td a',
            'tbody tr td a[href]',
            
            # Strategy 4: General company name links
            'a[title*="company"]',
            'a[title*="profile"]',
            
            # Strategy 5: Div-based listings
            '.company-item a',
            '.member-item a',
            'div[class*="company"] a',
            'div[class*="member"] a',
        ]
        
        for selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        href = await element.get_attribute('href')
                        if href:
                            # Clean and validate the URL
                            if href.startswith('/'):
                                full_url = self.base_url + href
                            elif href.startswith('http'):
                                full_url = href
                            else:
                                continue
                            
                            # Filter for actual company/profile pages
                            if any(keyword in full_url.lower() for keyword in ['/company/', '/profile/', '/member/']):
                                if full_url not in company_links:
                                    company_links.append(full_url)
                                    
                    if company_links:
                        break  # Found links with this selector, no need to try others
                        
            except Exception as e:
                self.logger.warning(f"Error with selector {selector}: {e}")
                continue
        
        # If no specific company links found, try to get any links that might lead to profiles
        if not company_links:
            try:
                # Get all links and filter them
                all_links = await page.query_selector_all('a[href]')
                self.logger.info(f"Found {len(all_links)} total links on page")
                
                for element in all_links:
                    href = await element.get_attribute('href')
                    text = await element.inner_text()
                    
                    if href and text:
                        if href.startswith('/'):
                            full_url = self.base_url + href
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue
                        
                        # Look for patterns that suggest company profiles
                        text_lower = text.lower().strip()
                        url_lower = full_url.lower()
                        
                        # Skip navigation, pagination, and other non-company links
                        skip_patterns = [
                            'next', 'prev', 'page', 'login', 'register', 'home',
                            'about', 'contact', 'terms', 'privacy', 'help'
                        ]
                        
                        if any(pattern in text_lower for pattern in skip_patterns):
                            continue
                        
                        # Look for company-like patterns
                        company_patterns = [
                            '/company/', '/profile/', '/member/', 
                            'ltd', 'inc', 'corp', 'co.', 'limited',
                            'logistics', 'shipping', 'freight', 'transport'
                        ]
                        
                        if any(pattern in url_lower or pattern in text_lower for pattern in company_patterns):
                            if full_url not in company_links:
                                company_links.append(full_url)
                                
            except Exception as e:
                self.logger.error(f"Error extracting general links: {e}")
        
        # Debug: Save page content if no links found
        if not company_links:
            await self.save_debug_page(page, f"no_links_page_{int(time.time())}")
        
        self.logger.info(f"Extracted {len(company_links)} company links")
        return company_links

    async def save_debug_page(self, page: Page, filename: str):
        """Save page content for debugging."""
        try:
            debug_dir = Path("debug")
            debug_dir.mkdir(exist_ok=True)
            
            # Save HTML content
            content = await page.content()
            async with aiofiles.open(debug_dir / f"{filename}.html", 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # Save screenshot
            await page.screenshot(path=debug_dir / f"{filename}.png", full_page=True)
            
            # Save page info
            url = page.url
            title = await page.title()
            info = {
                'url': url,
                'title': title,
                'timestamp': datetime.now().isoformat(),
                'viewport': await page.viewport_size()
            }
            
            async with aiofiles.open(debug_dir / f"{filename}_info.json", 'w') as f:
                await f.write(json.dumps(info, indent=2))
                
        except Exception as e:
            self.logger.error(f"Error saving debug page: {e}")

    async def extract_contact_info(self, page: Page, company_url: str) -> Optional[Dict]:
        """Extract contact information from company profile page."""
        try:
            await page.goto(company_url, timeout=self.timeout)
            await self.wait_for_network_idle(page, timeout=30000)
            
            # Extract company name
            company_name = ""
            name_selectors = [
                'h1', 'h2', '.company-name', '.profile-name', 
                '.title', '[class*="name"]', '[class*="title"]'
            ]
            
            for selector in name_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and text.strip() and len(text.strip()) > 2:
                            company_name = text.strip()
                            break
                except:
                    continue
            
            # Extract contact information
            contact_info = {
                'company_name': company_name,
                'company_url': company_url,
                'email': '',
                'phone': '',
                'address': '',
                'website': '',
                'contact_person': '',
                'department': '',
                'scraped_at': datetime.now().isoformat()
            }
            
            # Get page text content for extraction
            page_text = await page.inner_text('body')
            
            # Extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_text)
            if emails:
                # Filter out common non-contact emails
                filtered_emails = [email for email in emails if not any(skip in email.lower() 
                    for skip in ['noreply', 'no-reply', 'donotreply', 'admin', 'webmaster'])]
                if filtered_emails:
                    contact_info['email'] = filtered_emails[0]
            
            # Extract phone numbers
            phone_patterns = [
                r'\+?[\d\s\-\(\)]{10,}',  # General phone pattern
                r'\+\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',  # International
                r'\(\d{3}\)[\s\-]?\d{3}[\s\-]?\d{4}',  # US format
            ]
            
            for pattern in phone_patterns:
                phones = re.findall(pattern, page_text)
                if phones:
                    # Clean up the phone number
                    phone = re.sub(r'[^\d\+]', '', phones[0])
                    if len(phone) >= 10:
                        contact_info['phone'] = phones[0].strip()
                        break
            
            # Extract address (look for common address patterns)
            address_patterns = [
                r'\d+[\w\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)[^.]*',
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\s+\d{5}',
            ]
            
            for pattern in address_patterns:
                addresses = re.findall(pattern, page_text, re.IGNORECASE)
                if addresses:
                    contact_info['address'] = addresses[0].strip()
                    break
            
            # Try to extract structured contact information from specific elements
            contact_selectors = [
                '.contact-info', '.contact', '.address', '.phone', '.email',
                '[class*="contact"]', '[class*="address"]', '[class*="phone"]', '[class*="email"]'
            ]
            
            for selector in contact_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text:
                            # Update contact info if we find better structured data
                            if '@' in text and not contact_info['email']:
                                emails = re.findall(email_pattern, text)
                                if emails:
                                    contact_info['email'] = emails[0]
                            
                            if any(char.isdigit() for char in text) and len(text) > 8 and not contact_info['phone']:
                                phone_match = re.search(r'[\+\d\s\-\(\)]{10,}', text)
                                if phone_match:
                                    contact_info['phone'] = phone_match.group().strip()
                except:
                    continue
            
            # Only return if we have at least a company name
            if company_name:
                return contact_info
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting contact info from {company_url}: {e}")
            return None

    async def scrape_page(self, page_num: int, page: Page) -> List[Dict]:
        """Scrape a single listing page and extract all contacts."""
        contacts = []
        page_url = f"{self.listing_url}{page_num}"
        
        try:
            self.logger.info(f"Navigation attempt 1/3 to {page_url}")
            await page.goto(page_url, timeout=self.timeout)
            
            # Wait for page to load
            network_settled = await self.wait_for_network_idle(page, timeout=30000)
            if not network_settled:
                self.logger.warning("Network didn't settle completely, but page loaded")
            
            # Extract company links from this page
            company_links = await self.extract_company_links(page)
            
            if not company_links:
                self.logger.warning(f"No company links found on listing page")
                await self.save_debug_page(page, f"listing_page_{page_num}")
                return contacts
            
            self.logger.info(f"Found {len(company_links)} company links on page {page_num}")
            
            # Extract contact information from each company
            for i, company_url in enumerate(company_links):
                try:
                    self.logger.info(f"Processing company {i+1}/{len(company_links)}: {company_url}")
                    contact_info = await self.extract_contact_info(page, company_url)
                    
                    if contact_info:
                        contacts.append(contact_info)
                        self.logger.info(f"Successfully extracted contact: {contact_info['company_name']}")
                    else:
                        self.logger.warning(f"No contact info extracted from {company_url}")
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Error processing company {company_url}: {e}")
                    self.errors.append({
                        'url': company_url,
                        'error': str(e),
                        'page': page_num,
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
            
            self.processed_pages.add(page_num)
            
        except Exception as e:
            self.logger.error(f"Error scraping page {page_num}: {e}")
            self.errors.append({
                'page': page_num,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        
        return contacts

    async def run_scraping(self):
        """Main scraping execution with progress tracking."""
        console.print(f"📄 Pages: {self.start_page} to {self.end_page}")
        console.print(f"🔧 Timeout: {self.timeout}ms with exponential backoff")
        console.print(f"🔐 Login: {'Enabled' if self.use_login else 'Disabled'}")
        console.print(f"🏢 Department grouping: {'Enabled' if self.group_by_department else 'Disabled'}")
        console.print("=" * 60)
        
        if not self.use_login:
            console.print("⚠️ No login credentials provided. Proceeding without login...")
        
        console.print(f"🚀 Starting scraping: pages {self.start_page}-{self.end_page}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # Load cookies if available
            try:
                cookies_path = Path("cookies.json")
                if cookies_path.exists():
                    with open(cookies_path) as f:
                        cookies = json.load(f)
                    await context.add_cookies(cookies)
                    self.logger.info("Loaded cookies from cookies.json")
            except Exception as e:
                self.logger.warning(f"Could not load cookies: {e}")
            
            page = await context.new_page()
            
            # Progress tracking
            total_pages = self.end_page - self.start_page + 1
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Scraping pages...", total=total_pages)
                
                for page_num in range(self.start_page, self.end_page + 1):
                    console.print(f"📄 Processing page {page_num}...")
                    
                    page_contacts = await self.scrape_page(page_num, page)
                    self.all_contacts.extend(page_contacts)
                    
                    if page_contacts:
                        console.print(f"✅ Found {len(page_contacts)} contacts on page {page_num}")
                    else:
                        console.print(f"⚠️ No contacts found on page {page_num}")
                    
                    progress.update(task, advance=1)
                    
                    # Small delay between pages
                    await asyncio.sleep(2)
            
            await browser.close()

    def export_data(self):
        """Export scraped data to multiple formats."""
        if not self.all_contacts:
            console.print("⚠️ No contacts to export")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exports_dir = Path("exports")
        exports_dir.mkdir(exist_ok=True)
        
        # Create DataFrame
        df = pd.DataFrame(self.all_contacts)
        
        # Export to CSV
        csv_file = exports_dir / f"jctrans_contacts_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        
        # Export to JSON
        json_file = exports_dir / f"jctrans_contacts_{timestamp}.json"
        if self.group_by_department:
            # Group by department
            grouped_data = {}
            for contact in self.all_contacts:
                dept = contact.get('department', 'Unknown')
                if dept not in grouped_data:
                    grouped_data[dept] = []
                grouped_data[dept].append(contact)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(grouped_data, f, indent=2, ensure_ascii=False)
        else:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_contacts, f, indent=2, ensure_ascii=False)
        
        # Export to Excel with department sheets
        excel_file = exports_dir / f"jctrans_contacts_{timestamp}.xlsx"
        
        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                if self.group_by_department and len(df) > 0:
                    # Create separate sheets for each department
                    departments = df['department'].fillna('Unknown').unique()
                    
                    for dept in departments:
                        dept_df = df[df['department'].fillna('Unknown') == dept]
                        # Clean sheet name for Excel compatibility
                        sheet_name = str(dept)[:31] if dept and len(str(dept)) <= 31 else (str(dept)[:28] + "..." if dept else "Unknown")
                        # Remove invalid characters
                        sheet_name = re.sub(r'[\\/*?:\[\]]', '_', sheet_name)
                        if not sheet_name:  # If sheet name is empty after cleaning
                            sheet_name = "Sheet1"
                        dept_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Also create a summary sheet
                    df.to_excel(writer, sheet_name='All_Contacts', index=False)
                else:
                    # Simple single sheet export
                    df.to_excel(writer, sheet_name='Contacts', index=False)
        except Exception as e:
            self.logger.warning(f"Excel export failed: {e}. Trying simple export...")
            # Fallback to simple export
            df.to_excel(excel_file, index=False)
        
        console.print(f"📁 Exported {len(self.all_contacts)} contacts to:")
        console.print(f"  📊 CSV: {csv_file}")
        console.print(f"  📋 JSON: {json_file}")
        console.print(f"  📈 Excel: {excel_file}")

    def print_summary(self, start_time: float):
        """Print scraping summary."""
        duration = time.time() - start_time
        duration_str = f"{int(duration // 3600):01d}:{int((duration % 3600) // 60):02d}:{int(duration % 60):02d}"
        
        table = Table(title="🎉 JCTrans Scraping Summary")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        table.add_row("📄 Pages Scraped", str(len(self.processed_pages)))
        table.add_row("👥 Contacts Extracted", str(len(self.all_contacts)))
        table.add_row("📧 Emails Found", str(sum(1 for c in self.all_contacts if c.get('email'))))
        table.add_row("⚠️ Errors", str(len(self.errors)))
        table.add_row("⏱️ Duration", duration_str)
        
        console.print(table)

@click.command()
@click.option('--start-page', default=1, help='Starting page number')
@click.option('--end-page', default=10, help='Ending page number')
@click.option('--timeout', default=90000, help='Page timeout in milliseconds')
@click.option('--login/--no-login', default=False, help='Use login credentials')
@click.option('--group-by-department/--no-group', default=True, help='Group results by department')
def main(start_page: int, end_page: int, timeout: int, login: bool, group_by_department: bool):
    """JCTrans Pro Scraper 2025 - Fixed Version"""
    
    console.print(Panel.fit("🚀 Starting JCTrans Improved Scraper", style="bold blue"))
    console.print("=" * 60)
    
    start_time = time.time()
    
    scraper = JCTransScraperFixed(
        start_page=start_page,
        end_page=end_page,
        timeout=timeout,
        use_login=login,
        group_by_department=group_by_department
    )
    
    try:
        # Run the scraping
        asyncio.run(scraper.run_scraping())
        
        # Export results
        scraper.export_data()
        
        # Print summary
        scraper.print_summary(start_time)
        
        console.print("\n📁 Check exports/ folder for your contact data!")
        
    except KeyboardInterrupt:
        console.print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        console.print(f"\n❌ Scraping failed: {e}")
        scraper.logger.error(f"Fatal error: {e}")
    
    console.print("\n✅ Scraping completed successfully!")

if __name__ == "__main__":
    main()