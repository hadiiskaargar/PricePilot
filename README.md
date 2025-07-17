# 🏷️ PricePilot

Multi-Site Price Tracker with Dashboard, Alerts, and Trend History.

## 📦 Features

- ✅ Track prices from Amazon (eBay/Etsy placeholders removed for now)
- 📊 Interactive Streamlit Dashboard with trends
- ✉️ Email alerts for price drops
- 📸 Screenshot logging for debugging
- 💾 SQLite databases: `tracker.db` (URLs), `prices.db` (price history)

## 🚀 Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add URLs to track

```bash
python scraper.py --add https://a.co/d/example
```

### 3. Run scraper manually

```bash
python scraper.py
```

### 4. Launch dashboard

```bash
streamlit run dashboard.py
```

## 🧠 Project Structure

```
PricePilot/
│
├── scraper.py           # Scrapes all active product URLs
├── dashboard.py         # Streamlit dashboard with charts and tables
├── db_utils.py          # URL management + cascade delete logic
├── email_utils.py       # Sends alert emails (optional)
│
├── prices.db            # Stores scraped price history
├── tracker.db           # Stores tracked product URLs
│
├── sites/
│   └── amazon.py        # Site-specific scraping logic
│
├── screenshots/         # Automatic debug screenshots
├── .gitignore
├── README.md
└── requirements.txt
```

## ⚙️ Notes

- ❗ Product screenshots are saved in `screenshots/`
- ❗ Only Amazon works currently – you can extend to other sites
- ✔️ Tested with Playwright stealth mode + rotating user-agents
