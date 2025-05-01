from decimal import Decimal
from functools import lru_cache
from typing import Union

import requests
from loguru import logger

CRYPTOCOMPARE_API_KEY = "c70867ec2a1d3efddd6645c0ca05601efff07731850e7266761d0ee89e0d8527"
CRYPTOCOMPARE_API_URL = "https://min-api.cryptocompare.com/data/pricehistorical"


class PriceService:
    @staticmethod
    @lru_cache(maxsize=1024)
    def get_bitcoin_price(date: Union[int, float]) -> Decimal:
        """Obtém o preço histórico do Bitcoin em USD para o timestamp especificado."""
        params = {
            "fsym": "BTC",
            "tsyms": "USD",
            "ts": date,
            "api_key": CRYPTOCOMPARE_API_KEY,
        }
        try:
            r = requests.get(CRYPTOCOMPARE_API_URL, params=params, timeout=10)
            r.raise_for_status()
            price = r.json().get("BTC", {}).get("USD", 0)
            return Decimal(price)
        except requests.RequestException as e:
            logger.error(f"Erro ao adquirir cotação do bitcoin para timestamp {date}: {e}")
            return Decimal("0")
