import os
from pprint import pprint

import requests

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
CRYPTOCOMPARE_API_URL = os.getenv("CRYPTOCOMPARE_API_URL")


class PriceService:
    @staticmethod
    def get_bitcoin_price(date: str) -> float:
        params = {
            "fsym": "BTC",
            "tsyms": "USD",
            "ts": date,
            "api_key": CRYPTOCOMPARE_API_KEY,
        }
        r = requests.get(CRYPTOCOMPARE_API_URL, params=params)
        if r.status_code == 200:
            price = r.json().get("BTC", {}).get("USD", 0)
            return price

        return 0
