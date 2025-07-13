# PricePilot 🚀

A **well-structured MVP** for multi-site price tracking built with Playwright, SQLite, and Streamlit. This system demonstrates robust web scraping architecture while acknowledging real-world limitations.

## 📋 Overview

PricePilot is a **Minimum Viable Product (MVP)** that showcases technical architecture and scraping strategy. It's designed to track product prices across Amazon, eBay, and Etsy with a clean, extensible codebase suitable for portfolios or client demos.

### ✨ Features

- **Multi-site scraping**: Amazon, eBay, and Etsy support
- **Robust price extraction**: Handles various price formats and currencies
- **Real-time dashboard**: Streamlit-based visualization with filtering and export
- **Email alerts**: Price drop notifications
- **Comprehensive logging**: Debug information and screenshots for troubleshooting
- **Extensible architecture**: Easy to add new sites or features
- **Data persistence**: SQLite database with price history tracking

## 🏗 Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Scrapers  │───▶│  SQLite DB  │───▶│  Dashboard  │───▶│ Email Alerts│
│ (Playwright)│    │             │    │ (Streamlit) │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Core Components

- **Scrapers** (`sites/`): Modular, site-specific scraping logic
- **Database** (`prices.db`, `tracker.db`): Price history and product tracking
- **Dashboard** (`dashboard.py`): Real-time price visualization
- **Scheduler** (`scraper.py`): Automated daily scraping

## ⚙️ Tech Stack

- **Web Scraping**: Playwright (headless browser automation)
- **Database**: SQLite (lightweight, file-based)
- **Dashboard**: Streamlit (rapid web app development)
- **Language**: Python 3.8+
- **Scheduling**: `schedule` library
- **Email**: SMTP with MIME support

## 🛠 Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PricePilot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install
   ```

5. **Initialize databases**
   ```bash
   python scraper.py --once
   ```

## 🏁 Usage

### Running the Scraper

**One-time scraping:**
```bash
python scraper.py --once
```

**Scheduled scraping (daily at 10:00 AM):**
```bash
python scraper.py
```

### Running the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will be available at `http://localhost:8501`

### Adding Products

1. Open the dashboard
2. Use the sidebar to add product URLs
3. Select the appropriate source (Amazon, eBay, or Etsy)
4. The system will automatically start tracking prices

## 🧠 Known Limitations & Real-World Challenges

This MVP acknowledges the inherent challenges of web scraping in production environments:

### Amazon
- **Dynamic pricing**: Prices may be hidden until added to cart
- **Regional restrictions**: Some products unavailable in certain regions
- **A/B testing**: Different page layouts may affect selectors

### eBay
- **Cloudflare protection**: Anti-bot interstitials may appear
- **Dynamic content**: Prices loaded via JavaScript
- **Regional variations**: Different domains and layouts

### Etsy
- **Bot protection**: CAPTCHA and rate limiting
- **Dynamic pages**: Content loaded asynchronously
- **Seller variations**: Different shop layouts

### System Response
- **Detection**: Bot protection and unavailable products are detected and logged
- **Graceful degradation**: Returns "NA" for prices when extraction fails
- **Debugging**: Screenshots and detailed logs help identify issues
- **Transparency**: Dashboard clearly shows when data is unavailable

## 📊 Dashboard Features

- **Real-time price tracking**: Latest prices for all products
- **Price history charts**: Visual trends over time
- **Filtering**: By product, date range, and availability
- **Export functionality**: CSV and Excel export
- **Email alerts**: Toggle price drop notifications
- **Product management**: Add/remove tracked products

## 🚧 Roadmap / TODO

### Phase 1: Enhanced Scraping
- [ ] Add CAPTCHA bypass (Playwright Stealth or manual intervention)
- [ ] Proxy rotation and user-agent pool
- [ ] Implement retry logic with exponential backoff
- [ ] Add support for more e-commerce sites

### Phase 2: Infrastructure
- [ ] Deploy dashboard to Streamlit Cloud or Docker
- [ ] Switch to PostgreSQL or other scalable database
- [ ] Add Redis caching for improved performance
- [ ] Implement proper logging with rotation

### Phase 3: Advanced Features
- [ ] Add UI controls for bulk product management
- [ ] Enable tracking by category or keyword (not just product URLs)
- [ ] Implement price prediction algorithms
- [ ] Add mobile app or Telegram bot interface

### Phase 4: Production Ready
- [ ] Add comprehensive error handling and monitoring
- [ ] Implement rate limiting and respect robots.txt
- [ ] Add unit and integration tests
- [ ] Create deployment documentation

## 📁 Project Structure

```
PricePilot/
├── sites/                 # Site-specific scrapers
│   ├── amazon.py         # Amazon scraper
│   ├── ebay.py           # eBay scraper
│   └── etsy.py           # Etsy scraper
├── dashboard.py          # Streamlit dashboard
├── scraper.py            # Main scraping logic
├── db_utils.py           # Database utilities
├── email_utils.py        # Email alert functionality
├── test_fixes.py         # Test suite
├── requirements.txt      # Python dependencies
├── prices.db             # Price history database
├── tracker.db            # Product tracking database
└── screenshots/          # Debug screenshots
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file for email configuration:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Database Schema

- **`tracker.db`**: Product URLs and settings
- **`prices.db`**: Price history and product details

## 🐛 Troubleshooting

### Common Issues

1. **"NA" prices**: Check screenshots in `screenshots/` directory
2. **Bot detection**: Try different user agents or add delays
3. **Database errors**: Ensure write permissions in project directory
4. **Email alerts not working**: Verify SMTP configuration

### Debug Mode

Enable detailed logging by running:
```bash
python scraper.py --once --debug
```

## 🤝 Contributing

This is an MVP designed for learning and demonstration. Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and demonstration purposes. Please respect websites' terms of service and robots.txt files. The authors are not responsible for any misuse of this software.

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for reliable web automation
- Powered by [Streamlit](https://streamlit.io/) for rapid dashboard development
- Uses [SQLite](https://www.sqlite.org/) for lightweight data storage

---

**Note**: This MVP demonstrates understanding of web scraping challenges and how to design robust systems around them. It's suitable for technical portfolios and showcases real-world problem-solving skills. 


## Limitations

⚠️ **Note:** This MVP is designed for demonstration purposes. Due to anti-bot mechanisms and dynamic page structures on some target websites, real-time price scraping may occasionally return `"NA"` or fail to extract data without more advanced bypass techniques (e.g., captchas, stealth plugins, proxies).
