import os
from datetime import datetime
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import re

# Clean product title by removing extra spaces
def clean_title(title):
    return ' '.join(title.split()).strip()

# Clean and extract numeric price from text with improved logic
def extract_price(price_text):
    if not price_text:
        print(f"DEBUG: Empty price text received")
        return 'NA'
    
    print(f"DEBUG: Raw price text: '{price_text}'")
    
    # Remove common currency symbols and formatting
    cleaned = price_text.replace('$', '').replace('£', '').replace('€', '').strip()
    
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

# Main scraping function for an Amazon product
async def scrape_product(page, url):
    try:
        print(f"🔍 Starting Amazon scrape for: {url}")
        
        # Navigate to the product URL with shorter timeout and better error handling
        await page.goto(url, timeout=20000, wait_until='domcontentloaded')
        
        # Wait for the page to load and stabilize (shorter timeout)
        try:
            await page.wait_for_load_state('networkidle', timeout=5000)
        except:
            print("DEBUG: Network idle timeout, continuing anyway")
            pass
        
        # Check for bot protection or unavailable pages
        body_text = await page.content()
        if any(phrase in body_text.lower() for phrase in [
            'checking your browser', 'cloudflare', 'bot protection',
            'please wait', 'verifying you are human', 'captcha'
        ]):
            print("⚠️  Bot protection detected on Amazon page")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'product_name': 'Bot Protection Detected',
                'price': 'NA',
                'availability': 'Unknown',
                'url': url
            }
        
        # Wait for the product title to load (with fallback)
        title = "Unknown Product"
        title_selectors = [
            '#productTitle',
            'h1[data-automation-id="product-title"]',
            'h1.product-title',
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
        
        # Create screenshots directory if it doesn't exist
        os.makedirs('screenshots', exist_ok=True)
        
        # Take a screenshot for debugging (with timestamp)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = f"screenshots/amazon_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Comprehensive list of price selectors (ordered by reliability)
        price_selectors = [
            # Primary price selectors
            '#corePriceDisplay_desktop_feature_div span.a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#priceblock_saleprice',
            
            # Alternative price selectors
            'span.a-price span.a-offscreen',
            'span.a-price-whole',
            '.a-price .a-offscreen',
            '.a-price-range .a-offscreen',
            
            # Deal price selectors
            '.a-price.a-text-price .a-offscreen',
            '.a-price.a-text-price.a-size-base.a-color-secondary .a-offscreen',
            
            # Kindle and digital price selectors
            '#kindle-price',
            '#digital-list-price',
            
            # Used/New price selectors
            '.a-price.a-text-price.a-size-base.a-color-secondary',
            '.a-price.a-text-price.a-size-base.a-color-price',
            
            # Generic price selectors (fallback)
            'span.a-color-price',
            '.a-price',
            '[data-a-color="price"]',
            '.a-price-range',
        ]
        
        price = None
        used_selector = None
        
        # Try each selector until we find a price
        for selector in price_selectors:
            print(f"Trying selector: {selector}")
            try:
                # Try to find the element with strict=False for more flexibility
                element = await page.query_selector(selector, strict=False)
                if element:
                    price_text = await element.text_content()
                    if price_text and price_text.strip():
                        print(f"DEBUG: Found element with selector '{selector}': '{price_text}'")
                        price = extract_price(price_text)
                        used_selector = selector
                        if price != 'NA':
                            print(f"✅ Price found using selector: {selector}")
                            break
                        else:
                            print(f"Selector {selector} failed or returned None (price extraction failed)")
                else:
                    print(f"Selector {selector} failed or returned None (element not found)")
            except Exception as e:
                print(f"DEBUG: Error with selector '{selector}': {e}")
                continue
        
        # If no price found, try a more aggressive approach
        if not price or price == 'NA':
            print("DEBUG: Trying fallback price detection...")
            try:
                # Look for any element containing price-like patterns
                price_elements = await page.query_selector_all('[class*="price"], [id*="price"], [data-a-color="price"]')
                print(f"DEBUG: Found {len(price_elements)} potential price elements")
                
                for i, elem in enumerate(price_elements):
                    try:
                        text = await elem.text_content()
                        if text and re.search(r'\$[\d,]+\.?\d*', text):
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
        
        # Check availability status with multiple selectors
        availability = 'In Stock'
        availability_selectors = [
            '#availability span',
            '#availability',
            '.a-color-state',
            '[data-csa-c-type="availability"]',
            '.a-color-success',
            '.a-color-error'
        ]
        
        for avail_selector in availability_selectors:
            try:
                avail_elem = await page.query_selector(avail_selector)
                if avail_elem:
                    avail_text = await avail_elem.text_content()
                    if avail_text:
                        avail_lower = avail_text.lower()
                        if any(phrase in avail_lower for phrase in [
                            'out of stock', 'unavailable', 'currently unavailable',
                            'temporarily out of stock', 'we don\'t know when',
                            'no longer available', 'discontinued'
                        ]):
                            availability = 'Out of Stock'
                            print(f"⚠️  Product appears to be out of stock")
                            break
                        elif any(phrase in avail_lower for phrase in [
                            'in stock', 'available', 'ready to ship'
                        ]):
                            availability = 'In Stock'
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
        
    # Handle timeouts separately
    except PlaywrightTimeoutError as e:
        print(f"⏰ Timeout scraping {url}: {e}")
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'product_name': 'Timeout',
            'price': 'NA',
            'availability': 'Unknown',
            'url': url
        }
        
    # Catch-all for any other error
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'product_name': 'Error',
            'price': 'NA',
            'availability': 'Unknown',
            'url': url
        }
