import os
import threading
from datetime import datetime

import requests

CRYPTOCOMPARE_API_KEY = os.environ.get("CRYPTOCOMPARE_API_KEY")
CRYPTOCOMPARE_API_URL = os.environ.get("CRYPTOCOMPARE_API_URL")

price_cache = {}
lock = threading.Lock()


class PriceService:
    @staticmethod
    def get_bitcoin_price(date: datetime) -> float:
        key = date.strftime("%Y-%m-%d")
        with lock:
            if key in price_cache:
                return price_cache[key]

        timestamp = int(date.timestamp())
        params = {
            "fsym": "BTC",
            "tsyms": "USD",
            "ts": timestamp,
            "api_key": CRYPTOCOMPARE_API_KEY,
        }
        r = requests.get(CRYPTOCOMPARE_API_URL, params=params)
        if r.status_code == 200:
            price = r.json().get("BTC", {}).get("USD", 0)
            with lock:
                price_cache[key] = price
            return price
        return 0
