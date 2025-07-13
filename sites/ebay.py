import os
import asyncio
from datetime import datetime
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import re

def clean_title(title):
    return ' '.join(title.split()).strip()

def extract_price(price_text):
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
    try:
        print(f"🔍 Starting eBay scrape for: {url}")
        
        await page.goto(url, timeout=30000)
        await asyncio.sleep(5)  # Wait for anti-bot JS to finish
        
        # Check for bot-detection message
        body_text = await page.content()
        if any(phrase in body_text.lower() for phrase in [
            "ihr browser wird geprüft", "your browser is being checked", 
            "bot detection", "please wait", "checking your browser",
            "cloudflare", "verifying you are human", "captcha"
        ]):
            print(f"⚠️  Bot-detection page detected for {url}. Skipping scrape.")
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
            'h1',
            'h1[data-testid="x-item-title"]',
            'h1.x-item-title__mainTitle',
            '.x-item-title__mainTitle',
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
        
        # Screenshot for debugging
        os.makedirs('screenshots', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = f"screenshots/ebay_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Robust price selectors for eBay
        price_selectors = [
            'span.ux-textspans',  # New selector for EUR price
            'span#prcIsum',
            'span#mm-saleDscPrc',
            'span[itemprop="price"]',
            'span.s-item__price',
            'div.x-price-approx__price',
            'div.x-price-approx__value',
            'span.display-price',
            'span[itemprop="lowPrice"]',
            'span[itemprop="highPrice"]',
            'span[itemprop="offers"]',
            'div[itemprop="offers"] span',
            # Additional selectors for better coverage
            '.x-price-primary .ux-textspans',
            '.x-price-primary span',
            '.x-price-approx__price .ux-textspans',
            '.x-price-approx__value .ux-textspans',
            '[data-testid="x-price-primary"] .ux-textspans',
            '[data-testid="x-price-primary"] span',
        ]
        price = None
        used_selector = None
        for sel in price_selectors:
            print(f"Trying selector: {sel}")
            try:
                # Try with strict=False for more flexibility
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
                price_elements = await page.query_selector_all('[class*="price"], [id*="price"], [class*="Price"], [id*="Price"]')
                print(f"DEBUG: Found {len(price_elements)} potential price elements")
                
                for i, elem in enumerate(price_elements):
                    try:
                        text = await elem.text_content()
                        if text and re.search(r'\$|€|EUR|£', text):
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
        if not price or price == 'NA':
            print(f"⚠️  WARNING: Price not found for {url}")
            print(f"   Product: {title}")
            print(f"   Screenshot saved: {screenshot_path}")
            price = 'NA'
        else:
            print(f"💰 Price extracted: {price} for {title}")
        # Availability
        availability = 'In Stock'
        availability_selectors = [
            'span#qtySubTxt',
            '.x-item-condition__availability',
            '[data-testid="availability"]',
            '.s-item__availability',
        ]
        
        for avail_sel in availability_selectors:
            try:
                avail_elem = await page.query_selector(avail_sel)
                if avail_elem:
                    text = await avail_elem.text_content()
                    if text and any(phrase in text.lower() for phrase in [
                        'out of stock', 'unavailable', 'sold out', 'no longer available'
                    ]):
                        availability = 'Out of Stock'
                        print(f"⚠️  Product appears to be out of stock")
                        break
            except Exception:
                continue
        
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