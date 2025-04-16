import os

import requests

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")
CRYPTOCOMPARE_API_URL = os.getenv("CRYPTOCOMPARE_API_URL", "")


class PriceService:
    @staticmethod
    def get_bitcoin_price(date: str) -> float:
        params = {
            "fsym": "BTC",
            "tsyms": "USD",
            "ts": date,
            "api_key": CRYPTOCOMPARE_API_KEY,
        }
        try:
            r = requests.get(CRYPTOCOMPARE_API_URL, params=params)
            r.raise_for_status()
            price = r.json().get("BTC", {}).get("USD", 0)
            return price
        except requests.HTTPError as e:
            print(e)
        return 0
