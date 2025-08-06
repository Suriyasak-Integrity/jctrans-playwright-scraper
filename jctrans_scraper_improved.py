#!/usr/bin/env python3
"""
JCTrans Improved Scraper 2025
Extracts company information directly from listing pages for better efficiency.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import aiofiles
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

class JCTransImprovedScraper:
    """Improved JCTrans scraper that extracts data directly from listing pages."""
    
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
        
        console.print(Panel.fit("🚀 JCTrans Improved Scraper 2025 initialized", style="bold green"))

    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"jctrans_improved_{timestamp}.log"
        
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
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                await asyncio.sleep(2)
                return True
            except:
                return False

    async def extract_companies_from_listing(self, page: Page) -> List[Dict]:
        """Extract company information directly from the listing page."""
        companies = []
        
        try:
            # Wait for the company list to load
            await page.wait_for_selector('.membership-list-content-center-list-item', timeout=30000)
            
            # Get all company list items
            company_elements = await page.query_selector_all('.membership-list-content-center-list-item')
            self.logger.info(f"Found {len(company_elements)} company elements")
            
            for i, element in enumerate(company_elements):
                try:
                    company_data = await self.extract_company_data(element)
                    if company_data:
                        companies.append(company_data)
                        self.logger.info(f"Extracted company {i+1}: {company_data['company_name']}")
                    else:
                        self.logger.warning(f"Could not extract data for company element {i+1}")
                        
                except Exception as e:
                    self.logger.error(f"Error extracting company {i+1}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error finding company elements: {e}")
            # Save debug info
            await self.save_debug_page(page, f"error_listing_{int(time.time())}")
        
        return companies

    async def extract_company_data(self, element) -> Optional[Dict]:
        """Extract company data from a single company element."""
        try:
            company_data = {
                'company_name': '',
                'location': '',
                'city': '',
                'country': '',
                'services': [],
                'company_url': '',
                'membership_years': '',
                'membership_types': [],
                'description': '',
                'contact_available': False,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Extract company name
            name_element = await element.query_selector('.membership-list-font-bold')
            if name_element:
                company_data['company_name'] = (await name_element.inner_text()).strip()
            
            # Extract location
            location_element = await element.query_selector('.mem-icon-position + span')
            if location_element:
                location_text = (await location_element.inner_text()).strip()
                company_data['location'] = location_text
                
                # Parse city and country
                if ' - ' in location_text:
                    parts = location_text.split(' - ')
                    company_data['city'] = parts[0].strip()
                    company_data['country'] = parts[1].strip()
            
            # Extract company URL
            link_element = await element.query_selector('a[href*="/store/home/"]')
            if link_element:
                href = await link_element.get_attribute('href')
                if href:
                    if href.startswith('/'):
                        company_data['company_url'] = self.base_url + href
                    else:
                        company_data['company_url'] = href
            
            # Extract services
            service_elements = await element.query_selector_all('.mem-cond-tag')
            services = []
            for service_element in service_elements:
                service_text = (await service_element.inner_text()).strip()
                # Clean up service text (remove extra characters)
                service_text = re.sub(r'^\s*[+\d]+\s*$', '', service_text)  # Remove "+6" type indicators
                if service_text and service_text not in ['+1', '+2', '+3', '+4', '+5', '+6', '+7', '+8', '+9', '+10', '+11']:
                    services.append(service_text)
            company_data['services'] = services
            
            # Extract membership years
            years_element = await element.query_selector('.year-number')
            if years_element:
                years_text = (await years_element.inner_text()).strip()
                company_data['membership_years'] = years_text
            
            # Extract membership types (VIP codes)
            vip_elements = await element.query_selector_all('[class*="vip-code-"]')
            membership_types = []
            for vip_element in vip_elements:
                class_attr = await vip_element.get_attribute('class')
                if class_attr and 'vip-code-' in class_attr:
                    # Extract VIP level from class name
                    vip_match = re.search(r'vip-code-(\d+)', class_attr)
                    if vip_match:
                        membership_types.append(f"VIP Level {vip_match.group(1)}")
            company_data['membership_types'] = membership_types
            
            # Extract description
            desc_element = await element.query_selector('.mem-default-desc')
            if desc_element:
                company_data['description'] = (await desc_element.inner_text()).strip()
            
            # Check if "Get Contacts" button is available
            contact_button = await element.query_selector('.membership-list-content-center-list-item-right-button')
            if contact_button:
                button_text = (await contact_button.inner_text()).strip()
                company_data['contact_available'] = 'contact' in button_text.lower()
            
            # Only return if we have at least a company name
            if company_data['company_name']:
                return company_data
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting company data: {e}")
            return None

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

    async def scrape_page(self, page_num: int, page: Page) -> List[Dict]:
        """Scrape a single listing page and extract all companies."""
        contacts = []
        page_url = f"{self.listing_url}{page_num}"
        
        try:
            self.logger.info(f"Navigating to page {page_num}: {page_url}")
            await page.goto(page_url, timeout=self.timeout)
            
            # Wait for page to load
            network_settled = await self.wait_for_network_idle(page, timeout=30000)
            if not network_settled:
                self.logger.warning("Network didn't settle completely, but proceeding...")
            
            # Extract companies from this listing page
            companies = await self.extract_companies_from_listing(page)
            
            if not companies:
                self.logger.warning(f"No companies found on page {page_num}")
                await self.save_debug_page(page, f"no_companies_page_{page_num}")
                return contacts
            
            self.logger.info(f"Found {len(companies)} companies on page {page_num}")
            
            # Process each company
            for i, company_data in enumerate(companies):
                try:
                    # Add page information
                    company_data['source_page'] = page_num
                    company_data['source_url'] = page_url
                    
                    # Try to get more detailed information if company URL is available
                    if company_data.get('company_url') and company_data['contact_available']:
                        enhanced_data = await self.enhance_company_data(page, company_data)
                        if enhanced_data:
                            company_data.update(enhanced_data)
                    
                    contacts.append(company_data)
                    self.logger.info(f"Successfully processed company {i+1}: {company_data['company_name']}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing company {i+1}: {e}")
                    # Still add the basic data we have
                    contacts.append(company_data)
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

    async def enhance_company_data(self, page: Page, company_data: Dict) -> Optional[Dict]:
        """Try to get additional contact information from company page."""
        enhanced_data = {}
        
        try:
            company_url = company_data.get('company_url')
            if not company_url:
                return None
            
            self.logger.info(f"Enhancing data for: {company_data['company_name']}")
            
            # Navigate to company page
            await page.goto(company_url, timeout=30000)
            await asyncio.sleep(2)  # Give page time to load
            
            # Try to extract email addresses
            page_text = await page.inner_text('body')
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_text, re.IGNORECASE)
            
            # Filter and clean emails
            valid_emails = []
            for email in emails:
                email = email.lower().strip()
                if email and not any(skip in email for skip in ['noreply', 'no-reply', 'donotreply', 'admin@admin']):
                    if email not in valid_emails:
                        valid_emails.append(email)
            
            if valid_emails:
                enhanced_data['email'] = valid_emails[0]
                enhanced_data['all_emails'] = valid_emails
            
            # Try to extract phone numbers
            phone_patterns = [
                r'\+?[\d\s\-\(\)]{10,}',
                r'\+\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
            ]
            
            phones = []
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    phone = match.strip()
                    if len(re.sub(r'[^\d]', '', phone)) >= 10:
                        if phone not in phones:
                            phones.append(phone)
            
            if phones:
                enhanced_data['phone'] = phones[0]
                enhanced_data['all_phones'] = phones
            
            # Try to extract website
            website_patterns = [
                r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?',
                r'www\.[\w\-\.]+\.[\w]{2,}',
            ]
            
            websites = []
            for pattern in website_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    website = match.lower().strip()
                    if website and website not in websites and not website.endswith('.png') and not website.endswith('.jpg'):
                        if not website.startswith('http'):
                            website = 'https://' + website
                        websites.append(website)
            
            if websites:
                enhanced_data['website'] = websites[0]
                enhanced_data['all_websites'] = websites
            
            # Extract address information
            address_patterns = [
                r'\d+[\w\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)[^.]*',
                r'P\.?O\.?\s*Box\s+\d+[^,\n]*',
            ]
            
            addresses = []
            for pattern in address_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    address = match.strip()
                    if len(address) > 10 and address not in addresses:
                        addresses.append(address)
            
            if addresses:
                enhanced_data['address'] = addresses[0]
                enhanced_data['all_addresses'] = addresses
            
            return enhanced_data
            
        except Exception as e:
            self.logger.warning(f"Could not enhance data for {company_data['company_name']}: {e}")
            return None

    async def run_scraping(self):
        """Main scraping execution with progress tracking."""
        console.print(f"📄 Pages: {self.start_page} to {self.end_page}")
        console.print(f"🔧 Timeout: {self.timeout}ms")
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
                        console.print(f"✅ Found {len(page_contacts)} companies on page {page_num}")
                    else:
                        console.print(f"⚠️ No companies found on page {page_num}")
                    
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
        csv_file = exports_dir / f"jctrans_companies_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        
        # Export to JSON
        json_file = exports_dir / f"jctrans_companies_{timestamp}.json"
        if self.group_by_department:
            # Group by country
            grouped_data = {}
            for contact in self.all_contacts:
                country = contact.get('country', 'Unknown')
                if country not in grouped_data:
                    grouped_data[country] = []
                grouped_data[country].append(contact)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(grouped_data, f, indent=2, ensure_ascii=False)
        else:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_contacts, f, indent=2, ensure_ascii=False)
        
        # Export to Excel with country sheets
        excel_file = exports_dir / f"jctrans_companies_{timestamp}.xlsx"
        
        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                if self.group_by_department and len(df) > 0:
                    # Create separate sheets for each country
                    countries = df['country'].fillna('Unknown').unique()
                    
                    for country in countries:
                        country_df = df[df['country'].fillna('Unknown') == country]
                        # Clean sheet name for Excel compatibility
                        sheet_name = str(country)[:31] if country and len(str(country)) <= 31 else (str(country)[:28] + "..." if country else "Unknown")
                        # Remove invalid characters
                        sheet_name = re.sub(r'[\\/*?:\[\]]', '_', sheet_name)
                        if not sheet_name:
                            sheet_name = "Sheet1"
                        country_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Also create a summary sheet
                    df.to_excel(writer, sheet_name='All_Companies', index=False)
                else:
                    # Simple single sheet export
                    df.to_excel(writer, sheet_name='Companies', index=False)
        except Exception as e:
            self.logger.warning(f"Excel export failed: {e}. Trying simple export...")
            # Fallback to simple export
            df.to_excel(excel_file, index=False)
        
        console.print(f"📁 Exported {len(self.all_contacts)} companies to:")
        console.print(f"  📊 CSV: {csv_file}")
        console.print(f"  📋 JSON: {json_file}")
        console.print(f"  📈 Excel: {excel_file}")

    def print_summary(self, start_time: float):
        """Print scraping summary."""
        duration = time.time() - start_time
        duration_str = f"{int(duration // 3600):01d}:{int((duration % 3600) // 60):02d}:{int(duration % 60):02d}"
        
        table = Table(title="🎉 JCTrans Improved Scraping Summary")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        table.add_row("📄 Pages Scraped", str(len(self.processed_pages)))
        table.add_row("🏢 Companies Found", str(len(self.all_contacts)))
        table.add_row("📧 Emails Found", str(sum(1 for c in self.all_contacts if c.get('email'))))
        table.add_row("📞 Phones Found", str(sum(1 for c in self.all_contacts if c.get('phone'))))
        table.add_row("🌐 Websites Found", str(sum(1 for c in self.all_contacts if c.get('website'))))
        table.add_row("⚠️ Errors", str(len(self.errors)))
        table.add_row("⏱️ Duration", duration_str)
        
        console.print(table)

@click.command()
@click.option('--start-page', default=1, help='Starting page number')
@click.option('--end-page', default=10, help='Ending page number')
@click.option('--timeout', default=90000, help='Page timeout in milliseconds')
@click.option('--login/--no-login', default=False, help='Use login credentials')
@click.option('--group-by-department/--no-group', default=True, help='Group results by country')
def main(start_page: int, end_page: int, timeout: int, login: bool, group_by_department: bool):
    """JCTrans Improved Scraper 2025"""
    
    console.print(Panel.fit("🚀 Starting JCTrans Improved Scraper", style="bold blue"))
    console.print("=" * 60)
    
    start_time = time.time()
    
    scraper = JCTransImprovedScraper(
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
        
        console.print("\n📁 Check exports/ folder for your company data!")
        
    except KeyboardInterrupt:
        console.print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        console.print(f"\n❌ Scraping failed: {e}")
        scraper.logger.error(f"Fatal error: {e}")
    
    console.print("\n✅ Scraping completed successfully!")

if __name__ == "__main__":
    main()