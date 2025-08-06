#!/usr/bin/env python3
"""
JCTrans Contact Extractor (Improved)
Advanced contact information extraction and validation module.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse
import phonenumbers
from phonenumbers import NumberParseException


@dataclass
class ContactInfo:
    """Data class for storing extracted contact information."""
    company_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    website: str = ""
    contact_person: str = ""
    department: str = ""
    country: str = ""
    city: str = ""
    postal_code: str = ""
    fax: str = ""
    linkedin: str = ""
    company_type: str = ""
    services: List[str] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = []


class ImprovedContactExtractor:
    """Enhanced contact information extractor with improved pattern recognition."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_patterns()
    
    def setup_patterns(self):
        """Setup regex patterns for contact extraction."""
        
        # Email patterns
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'(?i)email[\s:]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
            r'(?i)e-mail[\s:]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
        ]
        
        # Phone patterns (international and local formats)
        self.phone_patterns = [
            r'\+\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}',  # International
            r'\(\d{3}\)[\s\-]?\d{3}[\s\-]?\d{4}',  # US format
            r'\d{3}[\s\-]?\d{3}[\s\-]?\d{4}',  # Basic US
            r'\+\d{1,3}[\s\(\-]?\d{1,4}[\s\)\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}',
            r'(?i)phone[\s:]*(\+?\d[\d\s\-\(\)]{8,})',
            r'(?i)tel[\s:]*(\+?\d[\d\s\-\(\)]{8,})',
            r'(?i)mobile[\s:]*(\+?\d[\d\s\-\(\)]{8,})',
        ]
        
        # Address patterns
        self.address_patterns = [
            r'\d+[\w\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct)[^.]*',
            r'(?i)address[\s:]*([^\n\r]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)[^\n\r]*)',
            r'\d+[^,\n]+,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\s+\d{5}',
            r'P\.?O\.?\s*Box\s+\d+[^,\n]*',
        ]
        
        # Website patterns
        self.website_patterns = [
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?',
            r'www\.[\w\-\.]+\.[\w]{2,}',
            r'(?i)website[\s:]*([^\s\n\r]+)',
            r'(?i)web[\s:]*([^\s\n\r]+)',
        ]
        
        # Contact person patterns
        self.person_patterns = [
            r'(?i)contact[\s:]*((?:[A-Z][a-z]+\s*){1,3})',
            r'(?i)manager[\s:]*((?:[A-Z][a-z]+\s*){1,3})',
            r'(?i)director[\s:]*((?:[A-Z][a-z]+\s*){1,3})',
            r'(?i)president[\s:]*((?:[A-Z][a-z]+\s*){1,3})',
            r'(?i)ceo[\s:]*((?:[A-Z][a-z]+\s*){1,3})',
            r'Mr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'Ms\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'Mrs\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]
        
        # Department patterns
        self.department_patterns = [
            r'(?i)(sales|marketing|operations|logistics|shipping|freight|customer\s*service|support|admin|finance|hr|human\s*resources)',
            r'(?i)department[\s:]*([^\n\r,]+)',
            r'(?i)division[\s:]*([^\n\r,]+)',
        ]
        
        # Postal code patterns
        self.postal_patterns = [
            r'\b\d{5}(?:-\d{4})?\b',  # US ZIP
            r'\b[A-Z]\d[A-Z]\s*\d[A-Z]\d\b',  # Canadian
            r'\b\d{4,6}\b',  # General numeric
        ]
        
        # Country patterns
        self.country_patterns = [
            r'(?i)\b(united states|usa|us|canada|china|japan|germany|france|uk|united kingdom|australia|singapore|hong kong|taiwan|south korea|india|brazil|mexico)\b'
        ]
        
        # Company type patterns
        self.company_type_patterns = [
            r'(?i)\b(ltd|limited|inc|incorporated|corp|corporation|llc|co\.|company|group|international|logistics|shipping|freight|transport|express|cargo|supply chain)\b'
        ]
        
        # Service patterns
        self.service_patterns = [
            r'(?i)\b(logistics|shipping|freight|transport|cargo|warehousing|distribution|supply chain|air freight|sea freight|ocean freight|trucking|rail|intermodal|customs|forwarding|3pl|4pl)\b'
        ]

    def extract_emails(self, text: str) -> List[str]:
        """Extract and validate email addresses."""
        emails = []
        
        for pattern in self.email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                email = match if isinstance(match, str) else match[0] if match else ""
                email = email.strip().lower()
                
                # Validate email format
                if self.is_valid_email(email):
                    # Filter out common non-contact emails
                    skip_emails = [
                        'noreply', 'no-reply', 'donotreply', 'admin@admin',
                        'webmaster', 'postmaster', 'info@info', 'test@test'
                    ]
                    
                    if not any(skip in email for skip in skip_emails):
                        if email not in emails:
                            emails.append(email)
        
        return emails

    def extract_phones(self, text: str) -> List[str]:
        """Extract and validate phone numbers."""
        phones = []
        
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                phone = match if isinstance(match, str) else match[0] if match else ""
                phone = phone.strip()
                
                # Clean and validate phone
                cleaned_phone = self.clean_phone_number(phone)
                if cleaned_phone and self.is_valid_phone(cleaned_phone):
                    if cleaned_phone not in phones:
                        phones.append(cleaned_phone)
        
        return phones

    def extract_addresses(self, text: str) -> List[str]:
        """Extract address information."""
        addresses = []
        
        for pattern in self.address_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                address = match if isinstance(match, str) else match[0] if match else ""
                address = address.strip()
                
                if len(address) > 10 and address not in addresses:
                    addresses.append(address)
        
        return addresses

    def extract_websites(self, text: str) -> List[str]:
        """Extract website URLs."""
        websites = []
        
        for pattern in self.website_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                website = match if isinstance(match, str) else match[0] if match else ""
                website = website.strip().lower()
                
                # Clean up website URL
                if not website.startswith(('http://', 'https://')):
                    if website.startswith('www.'):
                        website = 'https://' + website
                    elif '.' in website and not website.startswith('mailto:'):
                        website = 'https://' + website
                
                if self.is_valid_url(website) and website not in websites:
                    websites.append(website)
        
        return websites

    def extract_contact_persons(self, text: str) -> List[str]:
        """Extract contact person names."""
        persons = []
        
        for pattern in self.person_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                person = match if isinstance(match, str) else match[0] if match else ""
                person = person.strip()
                
                # Validate person name
                if len(person) > 2 and len(person) < 50 and person not in persons:
                    # Remove common titles and clean up
                    person = re.sub(r'(?i)^(mr\.?|ms\.?|mrs\.?|dr\.?|prof\.?)\s*', '', person)
                    if person and not person.lower() in ['contact', 'manager', 'director']:
                        persons.append(person.title())
        
        return persons

    def extract_departments(self, text: str) -> List[str]:
        """Extract department information."""
        departments = []
        
        for pattern in self.department_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                dept = match if isinstance(match, str) else match[0] if match else ""
                dept = dept.strip()
                
                if len(dept) > 2 and len(dept) < 50 and dept not in departments:
                    departments.append(dept.title())
        
        return departments

    def extract_postal_codes(self, text: str) -> List[str]:
        """Extract postal codes."""
        postal_codes = []
        
        for pattern in self.postal_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                postal = match.strip()
                if postal and postal not in postal_codes:
                    postal_codes.append(postal)
        
        return postal_codes

    def extract_countries(self, text: str) -> List[str]:
        """Extract country information."""
        countries = []
        
        for pattern in self.country_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                country = match.strip().title()
                if country not in countries:
                    countries.append(country)
        
        return countries

    def extract_company_types(self, text: str) -> List[str]:
        """Extract company type indicators."""
        types = []
        
        for pattern in self.company_type_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                comp_type = match.strip().upper()
                if comp_type not in types:
                    types.append(comp_type)
        
        return types

    def extract_services(self, text: str) -> List[str]:
        """Extract service offerings."""
        services = []
        
        for pattern in self.service_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                service = match.strip().title()
                if service not in services:
                    services.append(service)
        
        return services

    def is_valid_email(self, email: str) -> bool:
        """Validate email address format."""
        if not email or len(email) < 5:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number."""
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d\+]', '', phone)
        
        # Ensure minimum length
        if len(cleaned) < 10:
            return ""
        
        return phone.strip()  # Return original formatting for readability

    def is_valid_phone(self, phone: str) -> bool:
        """Validate phone number using phonenumbers library."""
        try:
            # Try to parse the phone number
            parsed = phonenumbers.parse(phone, None)
            return phonenumbers.is_valid_number(parsed)
        except NumberParseException:
            # Fallback to basic validation
            digits_only = re.sub(r'[^\d]', '', phone)
            return 10 <= len(digits_only) <= 15

    def is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and '.' in result.netloc
        except:
            return False

    def extract_comprehensive_contact_info(self, text: str, company_name: str = "", 
                                         company_url: str = "") -> ContactInfo:
        """Extract comprehensive contact information from text."""
        
        contact = ContactInfo()
        contact.company_name = company_name
        
        # Extract all information types
        emails = self.extract_emails(text)
        phones = self.extract_phones(text)
        addresses = self.extract_addresses(text)
        websites = self.extract_websites(text)
        persons = self.extract_contact_persons(text)
        departments = self.extract_departments(text)
        postal_codes = self.extract_postal_codes(text)
        countries = self.extract_countries(text)
        company_types = self.extract_company_types(text)
        services = self.extract_services(text)
        
        # Assign the best matches
        contact.email = emails[0] if emails else ""
        contact.phone = phones[0] if phones else ""
        contact.address = addresses[0] if addresses else ""
        contact.website = websites[0] if websites else ""
        contact.contact_person = persons[0] if persons else ""
        contact.department = departments[0] if departments else ""
        contact.postal_code = postal_codes[0] if postal_codes else ""
        contact.country = countries[0] if countries else ""
        contact.company_type = ", ".join(company_types[:3])  # Top 3 types
        contact.services = services[:10]  # Top 10 services
        
        # Extract city from address if available
        if contact.address:
            city_match = re.search(r',\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),', contact.address)
            if city_match:
                contact.city = city_match.group(1)
        
        return contact

    def validate_contact_info(self, contact: ContactInfo) -> Tuple[bool, List[str]]:
        """Validate extracted contact information and return issues."""
        issues = []
        is_valid = True
        
        # Check company name
        if not contact.company_name or len(contact.company_name) < 2:
            issues.append("Company name is missing or too short")
            is_valid = False
        
        # Check email
        if contact.email and not self.is_valid_email(contact.email):
            issues.append(f"Invalid email format: {contact.email}")
            is_valid = False
        
        # Check phone
        if contact.phone and not self.is_valid_phone(contact.phone):
            issues.append(f"Invalid phone format: {contact.phone}")
        
        # Check website
        if contact.website and not self.is_valid_url(contact.website):
            issues.append(f"Invalid website URL: {contact.website}")
        
        # Check if we have at least one contact method
        if not any([contact.email, contact.phone, contact.address, contact.website]):
            issues.append("No contact information found")
            is_valid = False
        
        return is_valid, issues

    def enhance_contact_with_context(self, contact: ContactInfo, page_url: str, 
                                   page_title: str = "") -> ContactInfo:
        """Enhance contact information with page context."""
        
        # Extract additional info from URL
        if page_url:
            parsed_url = urlparse(page_url)
            if not contact.website and parsed_url.netloc:
                contact.website = f"https://{parsed_url.netloc}"
        
        # Extract company name from page title if missing
        if not contact.company_name and page_title:
            # Clean up page title to extract company name
            title_clean = re.sub(r'(?i)\s*[-|]\s*(contact|about|profile|company).*$', '', page_title)
            if len(title_clean) > 2 and len(title_clean) < 100:
                contact.company_name = title_clean.strip()
        
        # Infer department from context if missing
        if not contact.department and any([contact.email, contact.phone]):
            if 'sales' in (contact.email + contact.phone).lower():
                contact.department = 'Sales'
            elif 'support' in (contact.email + contact.phone).lower():
                contact.department = 'Customer Support'
            elif 'info' in (contact.email + contact.phone).lower():
                contact.department = 'Information'
        
        return contact


# Utility functions for backwards compatibility
def extract_contact_info(text: str, company_name: str = "", 
                        company_url: str = "") -> Dict:
    """Legacy function for backwards compatibility."""
    extractor = ImprovedContactExtractor()
    contact = extractor.extract_comprehensive_contact_info(text, company_name, company_url)
    
    return {
        'company_name': contact.company_name,
        'email': contact.email,
        'phone': contact.phone,
        'address': contact.address,
        'website': contact.website,
        'contact_person': contact.contact_person,
        'department': contact.department,
        'country': contact.country,
        'city': contact.city,
        'postal_code': contact.postal_code,
        'company_type': contact.company_type,
        'services': contact.services
    }


if __name__ == "__main__":
    # Test the extractor
    sample_text = """
    ABC Logistics Ltd.
    Contact: John Smith, Sales Manager
    Email: john.smith@abclogistics.com
    Phone: +1-555-123-4567
    Address: 123 Main Street, New York, NY 10001
    Website: www.abclogistics.com
    Services: Air Freight, Ocean Shipping, Warehousing
    """
    
    extractor = ImprovedContactExtractor()
    contact = extractor.extract_comprehensive_contact_info(sample_text, "ABC Logistics Ltd.")
    
    print("Extracted Contact Information:")
    print(f"Company: {contact.company_name}")
    print(f"Email: {contact.email}")
    print(f"Phone: {contact.phone}")
    print(f"Address: {contact.address}")
    print(f"Website: {contact.website}")
    print(f"Contact Person: {contact.contact_person}")
    print(f"Department: {contact.department}")
    print(f"Services: {', '.join(contact.services)}")