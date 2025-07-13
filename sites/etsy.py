import os
from datetime import datetime
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import re

def clean_title(title):
    return ' '.join(title.split()).strip()

def extract_price(price_text):
    """Extract and normalize price from text with robust pattern matching."""
    if not price_text:
        print(f"DEBUG: Empty price text received")
        return 'NA'
    
    print(f"DEBUG: Raw price text: '{price_text}'")
    
    # Remove common currency symbols and formatting
    cleaned = price_text.replace('$', '').replace('£', '').replace('€', '').replace('EUR', '').strip()
    
    print(f"DEBUG: After currency removal: '{cleaned}'")
    
    # Handle different price formats
    # First, try to identify the format and normalize it
    if ',' in cleaned and '.' in cleaned:
        # Mixed format: 1,234.56 -> 1234.56 (US format)
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned and '.' not in cleaned:
        # Check if it's European format (comma as decimal separator)
        # Look for pattern like 99,99 (likely European) vs 1,234 (likely US thousands)
        if re.match(r'^\d{1,3},\d{2}$', cleaned):
            # European decimal format: 99,99 -> 99.99
            cleaned = cleaned.replace(',', '.')
        else:
            # US thousands format: 1,234 -> 1234
            cleaned = cleaned.replace(',', '')
    
    print(f"DEBUG: After format normalization: '{cleaned}'")
    
    # Now extract the price with simple patterns
    patterns = [
        r'(\d+(?:\.\d{1,2})?)',  # Simple decimal: 123.45 or 123
        r'(\d+)',                # Integer only: 123
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            price_str = match.group(1)
            print(f"DEBUG: Extracted price: '{price_str}'")
            return price_str
    
    print(f"DEBUG: No valid price pattern found in '{cleaned}'")
    return 'NA'

async def scrape_product(page, url):
    """Scrape product information from Etsy with improved reliability."""
    try:
        print(f"🔍 Starting Etsy scrape for: {url}")
        
        # Navigate to the product page
        await page.goto(url, timeout=30000, wait_until='domcontentloaded')
        
        # Wait for the page to load and stabilize
        try:
            await page.wait_for_load_state('networkidle', timeout=5000)
        except:
            print("DEBUG: Network idle timeout, continuing anyway")
            pass
        
        # Check for bot protection or unavailable pages
        body_text = await page.content()
        if any(phrase in body_text.lower() for phrase in [
            'checking your browser', 'cloudflare', 'bot protection',
            'please wait', 'verifying you are human'
        ]):
            print("⚠️  Bot protection detected on Etsy page")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'product_name': 'Bot Protection Detected',
                'price': 'NA',
                'availability': 'Unknown',
                'url': url
            }
        
        # Extract product title
        title = "Unknown Product"
        title_selectors = [
            'h1[data-buy-box-listing-title]',
            'h1[data-listing-id]',
            'h1.listing-page-title',
            'h1[data-testid="listing-page-title"]',
            'h1',
        ]
        
        for title_sel in title_selectors:
            try:
                await page.wait_for_selector(title_sel, timeout=5000)
                title = await page.eval_on_selector(title_sel, 'el => el.textContent')
                title = clean_title(title)
                print(f"✅ Title found using selector: {title_sel}")
                break
            except Exception as e:
                print(f"DEBUG: Title selector {title_sel} failed: {e}")
                continue
        
        # Take screenshot for debugging
        os.makedirs('screenshots', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = f"screenshots/etsy_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Comprehensive price selectors for Etsy
        price_selectors = [
            # Primary Etsy selectors
            'p[data-buy-box-region="price"] span[data-buy-box-region="price"]',
            'span[data-buy-box-region="price"]',
            'p[data-buy-box-region="price"]',
            
            # Alternative price selectors
            'span.currency-value',
            'div[data-buy-box-region="price"] span',
            'div[data-component="buybox"] span[data-buy-box-region="price"]',
            'span[data-buy-box-region="discounted-price"]',
            'span[data-buy-box-region="regular-price"]',
            
            # Generic price selectors
            '[data-testid="price"]',
            '.price',
            '.listing-price',
            '.buy-box-price',
            'span[class*="price"]',
            'div[class*="price"]',
            
            # Currency selectors
            'span[class*="currency"]',
            'div[class*="currency"]',
        ]
        
        price = None
        used_selector = None
        
        # Try each selector with detailed logging
        for sel in price_selectors:
            print(f"Trying selector: {sel}")
            try:
                # Use strict=False for more flexibility
                element = await page.query_selector(sel, strict=False)
                if element:
                    price_text = await element.text_content()
                    if price_text and price_text.strip():
                        print(f"DEBUG: Found element with selector '{sel}': '{price_text}'")
                        price = extract_price(price_text)
                        used_selector = sel
                        if price != 'NA':
                            print(f"✅ Price found using selector: {sel}")
                            break
                        else:
                            print(f"Selector {sel} failed or returned None (price extraction failed)")
                else:
                    print(f"Selector {sel} failed or returned None (element not found)")
            except Exception as e:
                print(f"DEBUG: Error with selector '{sel}': {e}")
                continue
        
        # Fallback: look for price-like patterns
        if not price or price == 'NA':
            print("DEBUG: Trying fallback price detection...")
            try:
                price_elements = await page.query_selector_all('[class*="price"], [id*="price"], [class*="Price"], [id*="Price"], [class*="currency"], [id*="currency"]')
                print(f"DEBUG: Found {len(price_elements)} potential price elements")
                
                for i, elem in enumerate(price_elements):
                    try:
                        text = await elem.text_content()
                        if text and re.search(r'\$|€|EUR|£|\d+', text):
                            print(f"DEBUG: Fallback element {i}: '{text.strip()}'")
                            price = extract_price(text)
                            used_selector = f"fallback pattern matching (element {i})"
                            if price != 'NA':
                                print(f"✅ Price found using fallback: {text.strip()}")
                                break
                    except Exception as e:
                        print(f"DEBUG: Error with fallback element {i}: {e}")
                        continue
            except Exception as e:
                print(f"DEBUG: Error in fallback detection: {e}")
        
        # Final price validation
        if not price or price == 'NA':
            print(f"⚠️  WARNING: Price not found for {url}")
            print(f"   Product: {title}")
            print(f"   Screenshot saved: {screenshot_path}")
            price = 'NA'
        else:
            print(f"💰 Price extracted: ${price} for {title}")
        
        # Check availability status
        availability = 'In Stock'
        availability_selectors = [
            'div[data-buy-box-region="sold-out-message"]',
            '.sold-out-message',
            '.unavailable-message',
            '[data-testid="sold-out"]',
            '.listing-unavailable',
        ]
        
        for avail_sel in availability_selectors:
            try:
                avail_elem = await page.query_selector(avail_sel)
                if avail_elem:
                    avail_text = await avail_elem.text_content()
                    if avail_text:
                        avail_lower = avail_text.lower()
                        if any(phrase in avail_lower for phrase in [
                            'sold out', 'unavailable', 'out of stock',
                            'no longer available', 'discontinued'
                        ]):
                            availability = 'Out of Stock'
                            print(f"⚠️  Product appears to be out of stock")
                            break
            except Exception:
                continue
        
        # Return the final structured product info
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'product_name': title,
            'price': price,
            'availability': availability,
            'url': url
        }
        
    except PlaywrightTimeoutError as e:
        print(f"⏰ Timeout scraping {url}: {e}")
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'product_name': 'Timeout',
            'price': 'NA',
            'availability': 'Unknown',
            'url': url
        }
        
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'product_name': 'Error',
            'price': 'NA',
            'availability': 'Unknown',
            'url': url
        } 