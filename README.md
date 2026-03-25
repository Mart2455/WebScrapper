# WebScrapper

A web scraping application with Discord webhook notifications. Scrapes target websites for updates and sends real-time alerts to a Discord channel.

## Features

- Scrape websites on a configurable schedule
- Parse and extract relevant data from pages
- Send formatted notifications to Discord via webhooks
- Configurable scraping targets and intervals

## Setup

### Prerequisites

- Python 3.10+
- A Discord webhook URL ([how to create one](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks))

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/WebScrapper.git
cd WebScrapper

# Create a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url
SCRAPE_INTERVAL=300  # seconds between scrapes
TARGET_URL=https://example.com
```

## Usage

```bash
python main.py
```

## Project Structure

```
WebScrapper/
├── main.py              # Entry point
├── scraper.py           # Web scraping logic
├── notifier.py          # Discord webhook notifications
├── config.py            # Configuration loader
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not tracked)
└── README.md
```

## Tech Stack

- **requests** / **httpx** — HTTP client for scraping
- **BeautifulSoup4** — HTML parsing
- **discord-webhook** — Discord notifications
- **python-dotenv** — Environment variable management
- **schedule** — Task scheduling