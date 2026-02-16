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
    'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
  'Content-Type': "application/json",
  'sec-ch-ua': "\"Chromium\";v=\"139\", \"Not;A=Brand\";v=\"99\"",
  'sec-ch-ua-mobile': "?1",
  'recaptchaiitl8n8t': "undefined",
  'sec-ch-ua-arch': "\"\"",
  'sec-ch-ua-full-version': "\"139.0.7339.0\"",
  'sec-ch-ua-platform-version': "\"15.0.0\"",
  'useraction': "",
  'sec-ch-ua-full-version-list': "\"Chromium\";v=\"139.0.7339.0\", \"Not;A=Brand\";v=\"99.0.0.0\"",
  'sec-ch-ua-bitness': "\"\"",
  'sec-ch-ua-model': "\"2310FPCA4G\"",
  'sec-ch-ua-platform': "\"Android\"",
  'origin': "https://m.donbet.com",
  'sec-fetch-site': "same-origin",
  'sec-fetch-mode': "cors",
  'sec-fetch-dest': "empty",
  'referer': "https://m.donbet.com/en/static/login",
  'accept-language': "en-US,en;q=0.9",
  'Cookie': "_ga=GA1.1.784298640.1763578350; _fbp=fb.1.1763578350224.350172994694383037; SessionId=33dd5c98-59f2-40f9-ae56-03b75c98a96c; UserIP=77927DDD028A4C32ED44D503D4CCDE9E; cf_clearance=xlUeIaMYVutySBOWI298Vy5yX83svLUvXkSedzbpysw-1769203325-1.2.1.1-4wX7kD7Ci_CFGVmqo_AMvx5yFUtuPrsktVBqStDdADzckNf.1mEhNVTpLF.hz26kSxWtTy5Mo9QSeZh3ZBDnX1uR4v2lxpN1bnNQGC6ZXv8z9nuNLO04Ety2SEwxS5xXNHEwnw_EJOXvZZRDUyxQLoHUOob19_hMGBZNq9Ex9cE3eZe9O1mgQPMFLiiGmkSluTuRHw02rIxHPxKLeU.hBjVZoFNYRUoiZrrNGlaQmiU; _ga_3WJE88DYKP=GS2.1.s1770336297$o87$g1$t1770336936$j42$l0$h0"
}