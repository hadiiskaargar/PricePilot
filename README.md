# PricePilot

**PricePilot** is a modern, extensible multi-site price tracker for e-commerce platforms. It scrapes product prices from Amazon, eBay, and Digikala (Amazon implemented, others ready for extension), stores them in an SQLite database, and visualizes price trends in a Streamlit dashboard.

---

## 🚀 Features
- **Multi-site scraping**: Modular architecture for Amazon, eBay, Digikala (Amazon ready, others easy to add)
- **Automated price tracking**: Schedule or run scrapes on demand
- **Historical price storage**: All data saved in SQLite
- **Interactive dashboard**: Visualize trends, filter, and export data
- **Email alerts**: Get notified of price drops
- **Proxy & stealth support**: Bypass anti-bot measures
- **Easy extensibility**: Add new sites with minimal code

---

## 🛠 Technologies Used
- [Playwright](https://playwright.dev/) (web scraping)
- [playwright-stealth](https://github.com/AtuboDad/playwright-stealth) (anti-bot)
- [Streamlit](https://streamlit.io/) (dashboard)
- [pandas](https://pandas.pydata.org/) (data analysis)
- [SQLAlchemy](https://www.sqlalchemy.org/) (ORM)
- [aiosqlite](https://github.com/omnilib/aiosqlite) (async SQLite)
- [openpyxl](https://openpyxl.readthedocs.io/) (Excel export)
- [schedule](https://schedule.readthedocs.io/) (job scheduling)

---

## ⚡ Quickstart

### 1. Clone the repository
```bash
git clone <repository-url>
cd PricePilot
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers (one-time)
```bash
playwright install
```

### 5. (Optional) Configure email alerts
Create a `.env` file in the project root:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

---

## 📈 Usage

### Run the Scraper
- **One-time scrape:**
  ```bash
  python scraper.py --once
  ```
- **Scheduled scraping (daily at 10:00 AM):**
  ```bash
  python scraper.py
  ```

### Run the Dashboard
```bash
streamlit run dashboard.py
```
Visit [http://localhost:8501](http://localhost:8501) in your browser.

### Add Product URLs
1. Open the dashboard sidebar
2. Enter the product URL (Amazon only, for now)
3. Click "Add URL" — tracking starts automatically

---

## 🖼 Example Dashboard

![Dashboard Screenshot](screenshots/dashboard_example.png)

---

## 🧩 Extending PricePilot

To add a new site (e.g., eBay, Digikala):
1. Create a new module in `sites/` (e.g., `ebay.py`)
2. Implement a `scrape_product(page, url, ...)` async function
3. Register the site in `scraper.py`'s `SITE_HANDLERS`
4. Update the dashboard to allow selecting the new source

---

## 🐞 Troubleshooting
- **NA prices:** Check screenshots in `screenshots/` for errors
- **Bot detection:** Try different user agents or proxies
- **Database errors:** Ensure you have write permissions
- **Email not working:** Check your `.env` SMTP settings

---

## 📁 Project Structure
```
PricePilot/
├── sites/           # Site-specific scrapers (amazon.py, etc.)
├── dashboard.py     # Streamlit dashboard
├── scraper.py       # Main scraping logic
├── db_utils.py      # Database utilities
├── email_utils.py   # Email alert logic
├── requirements.txt # Python dependencies
├── prices.db        # Price history database
├── tracker.db       # Product tracking database
├── screenshots/     # Debug screenshots
```

---

## 🤝 Contributing
1. Fork the repo
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

---

## 📄 License
MIT License. See [LICENSE](LICENSE).

---

## ⚠️ Disclaimer
This tool is for educational and demonstration purposes. Please respect websites' terms of service and robots.txt. The authors are not responsible for misuse.
# PricePilot
