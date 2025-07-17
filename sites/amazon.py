import os
import re
import random
import asyncio
from datetime import datetime
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async

# Clean product title by removing extra spaces
def clean_title(title):
    return ' '.join(title.split()).strip() if title else 'Unknown Product'

# Clean and extract numeric price from text with improved logic
def extract_price(price_text):
    if not price_text:
        print(f"DEBUG: Empty price text received")
        return 'NA'
    print(f"DEBUG: Raw price text: '{price_text}'")
    cleaned = price_text.replace('$', '').replace('£', '').replace('€', '').strip()
    print(f"DEBUG: After currency removal: '{cleaned}'")
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned and '.' not in cleaned:
        if re.match(r'^\d{1,3},\d{2}$', cleaned):
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    print(f"DEBUG: After format normalization: '{cleaned}'")
    patterns = [
        r'(\d+(?:\.\d{1,2})?)',
        r'(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            price_str = match.group(1)
            print(f"DEBUG: Extracted price: '{price_str}'")
            return price_str
    print(f"DEBUG: No valid price pattern found in '{cleaned}'")
    return 'NA'

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
]

async def scrape_product(page, url, *, proxy=None, user_agent=None, playwright=None, max_retries=3):
    attempt = 0
    last_error = None
    while attempt < max_retries:
        try:
            # Create context/page if playwright is provided
            if playwright is not None:
                ua = user_agent or random.choice(USER_AGENTS)
                context_args = {
                    'user_agent': ua,
                    'locale': 'en-US',
                    'timezone_id': 'America/New_York',
                    'viewport': {'width': 1440, 'height': 900},
                    'color_scheme': 'light',
                    'permissions': ['geolocation'],
                    'geolocation': {'longitude': -77.0364, 'latitude': 38.8951},
                }
                if proxy:
                    context_args['proxy'] = { 'server': proxy }
                context = await playwright.chromium.new_context(**context_args)
                page = await context.new_page()
            else:
                context = None
                ua = user_agent or random.choice(USER_AGENTS)
            print(f"Using user-agent: {ua}")
            await stealth_async(page)
            print(f"🔍 Starting Amazon scrape for: {url} (UA: {ua}, Proxy: {proxy})")
            await page.goto(url, timeout=20000, wait_until='domcontentloaded')
            await asyncio.sleep(3)  # Wait for dynamic content
            os.makedirs('screenshots', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            debug_screenshot_path = f"screenshots/amazon_debug_{timestamp}.png"
            await page.screenshot(path=debug_screenshot_path, full_page=True)
            print(f"📸 Debug screenshot after wait saved: {debug_screenshot_path}")
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                print("DEBUG: Network idle timeout, continuing anyway")
            # Check for bot protection
            body_text = await page.content()
            if any(phrase in body_text.lower() for phrase in [
                'checking your browser', 'cloudflare', 'bot protection',
                'please wait', 'verifying you are human', 'captcha',
                'enter the characters you see below', 'sorry, we just need to make sure',
            ]):
                print("⚠️  Bot protection detected on Amazon page")
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_path = f"screenshots/amazon_botprotect_{timestamp}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Screenshot saved: {screenshot_path}")
                if context:
                    await context.close()
                attempt += 1
                if attempt < max_retries:
                    print(f"🔁 Retrying after 10s with new user-agent/proxy (attempt {attempt+1}/{max_retries})...")
                    await asyncio.sleep(10)
                    user_agent = random.choice([ua for ua in USER_AGENTS if ua != ua])
                    continue
                else:
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
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f"screenshots/amazon_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved: {screenshot_path}")
            # Price selectors (2025 update: prioritize buybox and a-offscreen)
            price_selectors = [
                '#corePriceDisplay_desktop_feature_div span.a-price.aok-align-center span.a-offscreen',
                '#corePriceDisplay_desktop_feature_div span.a-offscreen',
                '#buybox span.a-offscreen',
                '#priceblock_ourprice',
                '#priceblock_dealprice',
                '#priceblock_saleprice',
                'span.a-price span.a-offscreen',
                'span.a-price-whole',
                '.a-price .a-offscreen',
                '.a-price-range .a-offscreen',
                '.a-price.a-text-price .a-offscreen',
                '.a-price.a-text-price.a-size-base.a-color-secondary .a-offscreen',
                '#kindle-price',
                '#digital-list-price',
                '.a-price.a-text-price.a-size-base.a-color-secondary',
                '.a-price.a-text-price.a-size-base.a-color-price',
                'span.a-color-price',
                '.a-price',
                '[data-a-color="price"]',
                '.a-price-range',
                'span.a-offscreen',
            ]
            price = None
            used_selector = None
            for selector in price_selectors:
                print(f"Trying selector: {selector}")
                try:
                    element = await page.query_selector(selector, strict=False)
                    if element:
                        price_text = await element.text_content()
                        if price_text and price_text.strip():
                            print(f"DEBUG: Found element with selector '{selector}': '{price_text}'")
                            price = extract_price(price_text)
                            used_selector = selector
                            if price != 'NA':
                                try:
                                    price = float(price)
                                except Exception:
                                    pass
                                print(f"✅ Price found using selector: {selector}")
                                break
                            else:
                                print(f"Selector {selector} failed or returned None (price extraction failed)")
                    else:
                        print(f"Selector {selector} failed or returned None (element not found)")
                except Exception as e:
                    print(f"DEBUG: Error with selector '{selector}': {e}")
                    continue
            # Fallback price detection
            if not price or price == 'NA':
                print("DEBUG: Trying fallback price detection...")
                try:
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
            # Filter out non-shippable items
            if price and price != 'NA' and 'cannot be shipped' in body_text.lower():
                print(f"⚠️  This item cannot be shipped to your location. Ignoring price.")
                price = 'NA'
            if not price or price == 'NA':
                print(f"⚠️  WARNING: Price not found for {url}")
                print(f"   Product: {title}")
                print(f"   Screenshot saved: {screenshot_path}")
                price = 'NA'
            else:
                print(f"💰 Price extracted: ${price} for {title}")
            # Availability
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
            if context:
                await context.close()
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'product_name': title,
                'price': price,
                'availability': availability,
                'url': url
            }
        except PlaywrightTimeoutError as e:
            print(f"⏰ Timeout scraping {url}: {e}")
            last_error = e
            try:
                os.makedirs('screenshots', exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_path = f"screenshots/amazon_timeout_{timestamp}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Screenshot saved: {screenshot_path}")
            except Exception:
                pass
            if context:
                await context.close()
            attempt += 1
            if attempt < max_retries:
                print(f"🔁 Retrying after 10s (timeout, attempt {attempt+1}/{max_retries})...")
                await asyncio.sleep(10)
                continue
            else:
                return {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'product_name': 'Timeout',
                    'price': 'NA',
                    'availability': 'Unknown',
                    'url': url
                }
        except Exception as e:
            last_error = e
            print(f"Error during scraping attempt {attempt+1}: {e}")
            if context:
                await context.close()
            attempt += 1
            if attempt < max_retries:
                print(f"🔁 Retrying after 10s (attempt {attempt+1}/{max_retries})...")
                await asyncio.sleep(10)
            else:
                return {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'product_name': 'Scraping Error',
                    'price': 'NA',
                    'availability': 'Unknown',
                    'url': url
                }
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'product_name': 'Error',
        'price': 'NA',
        'availability': 'Unknown',
        'url': url
    }
