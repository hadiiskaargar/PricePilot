import streamlit as st
import pandas as pd
from datetime import datetime
from db_utils import init_db, add_url, get_urls, delete_url, set_email_alerts, get_email_alerts
from sqlalchemy import create_engine, select, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Init DB on first run ---
init_db()

st.set_page_config(page_title="Multi-Site Price Tracker Dashboard", layout="wide")
st.title("📈 Multi-Site Price Tracker Dashboard")

# --- Sidebar: Add Product URL ---
st.sidebar.header("Add Product URL")
with st.sidebar.form("add_url_form"):
    new_url = st.text_input("Product URL", "")
    new_source = st.selectbox("Source", ["amazon", "ebay", "etsy"])
    submitted = st.form_submit_button("Add URL")
    if submitted and new_url:
        add_url(new_url.strip(), new_source)
        st.success(f"Added: {new_url}")
        st.rerun()

# --- Sidebar: Email Alerts Toggle ---
st.sidebar.header("Email Alerts")
email_enabled = get_email_alerts()
new_email_enabled = st.sidebar.toggle("Enable Email Alerts", value=email_enabled)
if new_email_enabled != email_enabled:
    set_email_alerts(new_email_enabled)
    st.rerun()

st.sidebar.write(f"Current status: {'Enabled' if get_email_alerts() else 'Disabled'}")

# --- Sidebar: Tracked Products Table ---
st.sidebar.header("Tracked Products")
urls = get_urls()  # List of (id, url, source, created_at)
if urls:
    for id, url, source, created_at in urls:
        col1, col2 = st.sidebar.columns([4,1])
        col1.write(f"{source.title()}: {url}")
        if col2.button("Delete", key=f"del_{id}"):
            delete_url(id)
            st.rerun()
else:
    st.sidebar.info("No products being tracked.")

# --- Database setup for price data ---
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
DATABASE_URL = 'sqlite:///prices.db'
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)

def load_data():
    """Load price data with improved error handling and orphaned data filtering."""
    try:
        with SessionLocal() as session:
            # Get all tracked URLs from tracker.db to filter out orphaned data
            tracked_urls = set()
            try:
                import sqlite3
                tracker_conn = sqlite3.connect('tracker.db')
                tracker_c = tracker_conn.cursor()
                tracker_c.execute('SELECT url FROM products')
                tracked_urls = {row[0] for row in tracker_c.fetchall()}
                tracker_conn.close()
            except Exception as e:
                st.error(f"Error accessing tracker.db: {e}")
                return pd.DataFrame()
            
            # Only load products that are still being tracked
            q = session.query(PriceHistory, Product).join(Product, PriceHistory.product_id == Product.id)
            rows = q.all()
            
            if not rows:
                return pd.DataFrame()
            
            data = []
            for ph, prod in rows:
                # Only include products that are still being tracked
                if prod.url in tracked_urls:
                    data.append({
                        'date': ph.date,
                        'product_name': prod.name,
                        'price': ph.price,
                        'availability': ph.availability,
                        'url': prod.url
                    })
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            # Ensure price is always numeric
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            return df
            
    except Exception as e:
        st.error(f"Error loading price data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No price data available in the database. Run the scraper to collect data.")
    st.stop()

# --- Sidebar filters ---
st.sidebar.header("Filters")
product_options = sorted(df['product_name'].unique())
product_filter = st.sidebar.multiselect("Product", product_options, default=product_options)
date_min = df['date'].min()
date_max = df['date'].max()
date_range = st.sidebar.date_input("Date range", [date_min, date_max], min_value=date_min, max_value=date_max)

filtered_df = df[df['product_name'].isin(product_filter)]
filtered_df = filtered_df[(filtered_df['date'] >= pd.to_datetime(date_range[0])) & (filtered_df['date'] <= pd.to_datetime(date_range[1]))]

# --- Export buttons ---
st.sidebar.header("Export Data")
export_csv = st.sidebar.button("Export to CSV")
export_excel = st.sidebar.button("Export to Excel")
if export_csv:
    st.sidebar.download_button(
        label="Download CSV",
        data=filtered_df.to_csv(index=False),
        file_name="price_data.csv",
        mime="text/csv"
    )
if export_excel:
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False)
    st.sidebar.download_button(
        label="Download Excel",
        data=output.getvalue(),
        file_name="price_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Show latest prices ---
st.subheader("Latest Prices")
latest = filtered_df.sort_values('date').groupby('product_name').tail(1)
for _, row in latest.iterrows():
    st.metric(
        label=row['product_name'],
        value=f"${row['price'] if pd.notnull(row['price']) else 'NA'}",
        delta=None,
        help=f"{row['url']} | Availability: {row['availability']}"
    )

# --- Price trends ---
st.subheader("Price Trends")
for product in filtered_df['product_name'].unique():
    prod_df = filtered_df[filtered_df['product_name'] == product].sort_values('date')
    st.markdown(f"**{product}**")
    st.line_chart(prod_df.set_index('date')['price'])

# --- Show raw data ---
with st.expander("Show raw data"):
    st.dataframe(filtered_df) 