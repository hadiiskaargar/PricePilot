import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional

DB_PATH = 'tracker.db'
PRICES_DB_PATH = 'prices.db'

# --- Database Setup and Utilities ---
def init_db():
    """Create the tracker.db database with products and settings tables if not exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Ensure email_alerts setting exists
    c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('email_alerts', '1'))
    conn.commit()
    conn.close()

def add_url(url: str, source: str) -> int:
    """Insert a new product URL and return its ID."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO products (url, source, created_at) VALUES (?, ?, ?)',
              (url, source, datetime.utcnow().isoformat()))
    conn.commit()
    c.execute('SELECT id FROM products WHERE url = ?', (url,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else -1

def get_urls() -> List[Tuple[int, str, str, str]]:
    """Return a list of all saved product URLs as (id, url, source, created_at)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, url, source, created_at FROM products ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def delete_url(id: int) -> None:
    """Delete a product by its ID with cascade deletion from prices.db."""
    # First, get the URL from tracker.db
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT url FROM products WHERE id = ?', (id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        print(f"Product with ID {id} not found in tracker.db")
        return
    
    url = row[0]
    
    # Delete from tracker.db
    c.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    # Cascade delete from prices.db
    try:
        prices_conn = sqlite3.connect(PRICES_DB_PATH)
        prices_c = prices_conn.cursor()
        
        # First, find the product in the product table
        prices_c.execute('SELECT id FROM product WHERE url = ?', (url,))
        product_row = prices_c.fetchone()
        
        if product_row:
            product_id = product_row[0]
            
            # Delete all price history entries for this product
            prices_c.execute('DELETE FROM pricehistory WHERE product_id = ?', (product_id,))
            print(f"Deleted {prices_c.rowcount} price history entries for product {product_id}")
            
            # Delete the product itself
            prices_c.execute('DELETE FROM product WHERE id = ?', (product_id,))
            print(f"Deleted product {product_id} from prices.db")
            
            prices_conn.commit()
        else:
            print(f"Product with URL {url} not found in prices.db")
        
        prices_conn.close()
        
    except Exception as e:
        print(f"Error during cascade deletion from prices.db: {e}")
        # Don't fail the main deletion if cascade fails

def set_email_alerts(enabled: bool) -> None:
    """Set the global email alerts toggle in the settings table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', ('email_alerts', '1' if enabled else '0'))
    conn.commit()
    conn.close()

def get_email_alerts() -> bool:
    """Get the current global email alerts toggle state."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', ('email_alerts',))
    row = c.fetchone()
    conn.close()
    return row[0] == '1' if row else True 