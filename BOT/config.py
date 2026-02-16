import os
from pathlib import Path

# Telegram Bot Config
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8594923186:AAE1HWhu_dwHDz0o6pljO1Mbk1nPRQvBgrQ")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", 8135760174))

# Paths
BASE_DIR = Path(__file__).parent
SITES_DIR = BASE_DIR / "sites"
RESULTS_DIR = BASE_DIR / "results"

# Create directories
RESULTS_DIR.mkdir(exist_ok=True)

# Threading
MAX_WORKERS = 1
REQUEST_TIMEOUT = 30

# Default Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}