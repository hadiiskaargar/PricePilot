import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv
import schedule
import time
import importlib
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, select, UniqueConstraint, delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_utils import send_price_drop_alert
from db_utils import get_urls, get_email_alerts, init_db

# Clean product title
def clean_title(title):
    return ' '.join(title.split()).strip()

# Clean product availability
def clean_availability(avail):
    if not avail:
        return 'Unknown'
    return ' '.join(avail.split()).strip()

# --- Modular multi-site scraping support ---
# Detect site from URL and delegate to site-specific handler
SITE_HANDLERS = {
    'amazon': 'sites.amazon',
    'ebay': 'sites.ebay',
    'etsy': 'sites.etsy',
}

def detect_site(source):
    if source == 'amazon':
        return 'amazon'
    elif source == 'ebay':
        return 'ebay'
    elif source == 'etsy':
        return 'etsy'
    return None

async def scrape_product(page, url):
    site = detect_site(url)
    if not site or site not in SITE_HANDLERS:
        print(f"Unsupported site for URL: {url}")
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'product_name': 'Unsupported site',
            'price': 'NA',
            'url': url
        }
    handler_module = importlib.import_module(SITE_HANDLERS[site])
    return await handler_module.scrape_product(page, url)

# --- Database setup ---
Base = declarative_base()

class Product(Base):
    __tablename__ = 'product'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)

class PriceHistory(Base):
    __tablename__ = 'pricehistory'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    date = Column(Date, nullable=False)
    price = Column(Float, nullable=True)
    availability = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint('product_id', 'date', name='_product_date_uc'),)

DATABASE_URL = 'sqlite+aiosqlite:///prices.db'
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def cleanup_orphaned_data():
    """Remove orphaned data from prices.db that no longer exists in tracker.db."""
    try:
        # Get all tracked URLs from tracker.db
        import sqlite3
        tracker_conn = sqlite3.connect('tracker.db')
        tracker_c = tracker_conn.cursor()
        tracker_c.execute('SELECT url FROM products')
        tracked_urls = {row[0] for row in tracker_c.fetchall()}
        tracker_conn.close()
        
        async with AsyncSessionLocal() as session:
            # Find products in prices.db that are no longer tracked
            all_products = await session.execute(select(Product))
            orphaned_products = []
            
            for product in all_products.scalars():
                if product.url not in tracked_urls:
                    orphaned_products.append(product.id)
            
            if orphaned_products:
                # Delete price history for orphaned products
                await session.execute(
                    delete(PriceHistory).where(PriceHistory.product_id.in_(orphaned_products))
                )
                
                # Delete orphaned products
                await session.execute(
                    delete(Product).where(Product.id.in_(orphaned_products))
                )
                
                await session.commit()
                print(f"Cleaned up {len(orphaned_products)} orphaned products and their price history")
            else:
                print("No orphaned data found")
                
    except Exception as e:
        print(f"Error during cleanup: {e}")

async def save_to_db(results):
    alerted = set()  # (product_id, old_price, new_price)
    email_enabled = get_email_alerts()
    async with AsyncSessionLocal() as session:
        for row in results:
            # Clean product name and availability
            row['product_name'] = clean_title(row['product_name'])
            row['availability'] = clean_availability(row.get('availability', 'Unknown'))
            # Upsert product
            stmt = sqlite_insert(Product).values(name=row['product_name'], url=row['url'])
            stmt = stmt.on_conflict_do_update(index_elements=['url'], set_={'name': row['product_name']})
            await session.execute(stmt)
            await session.commit()
            # Get product id
            prod = await session.execute(select(Product).where(Product.url == row['url']))
            prod_id = prod.scalar_one().id
            # Insert price history
            price_val = float(row['price']) if row['price'] not in (None, '', 'NA') else None
            today = datetime.now().date()
            # Get previous price (before today)
            prev = await session.execute(
                select(PriceHistory).where(
                    PriceHistory.product_id == prod_id,
                    PriceHistory.date < today
                ).order_by(PriceHistory.date.desc())
            )
            prev_row = prev.scalars().first()
            # Check if record already exists
            existing = await session.execute(
                select(PriceHistory).where(
                    PriceHistory.product_id == prod_id,
                    PriceHistory.date == today
                )
            )
            if existing.scalar() is None:
                ph = PriceHistory(product_id=prod_id, date=today, price=price_val, availability=row['availability'])
                session.add(ph)
                await session.commit()
            else:
                print(f"Skipped duplicate entry for product_id={prod_id} on {today}")

            # Price drop alert
            if email_enabled and prev_row and prev_row.price is not None and price_val is not None and price_val < prev_row.price:
                alert_key = (prod_id, prev_row.price, price_val)
                if alert_key not in alerted:
                    try:
                        send_price_drop_alert(row['product_name'], prev_row.price, price_val, row['url'])
                        alerted.add(alert_key)
                    except Exception as e:
                        print(f"Error sending price drop alert: {e}")
        await session.commit()

# Main scraping logic
async def scrape_all():
    # Clean up orphaned data first
    await cleanup_orphaned_data()
    
    urls = get_urls()  # List of (id, url, source, created_at)
    if not urls:
        print("No URLs found in database.")
        return
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")
        page = await context.new_page()
        for _, url, source, _ in urls:
            print(f"Scraping: {url}")
            site = detect_site(source)
            if not site:
                print(f"Unknown source for URL: {url}")
                continue
            handler_module = importlib.import_module(SITE_HANDLERS[site])
            data = await handler_module.scrape_product(page, url)
            results.append(data)
        await browser.close()
    await save_to_db(results)
    print("Scraping complete. Data saved to SQLite database.")

# Scheduler job
def job():
    asyncio.run(scrape_all())

if __name__ == '__main__':
    import sys
    asyncio.run(init_db())
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        asyncio.run(scrape_all())
    else:
        print("Starting scheduled scraping (daily at 10:00 AM)...")
        schedule.every().day.at("10:00").do(lambda: asyncio.run(scrape_all()))
        while True:
            schedule.run_pending()
            time.sleep(60) 