import os
from decimal import Decimal
from functools import lru_cache

import requests
from loguru import logger

CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")
CRYPTOCOMPARE_API_URL = os.getenv("CRYPTOCOMPARE_API_URL", "")


class PriceService:
    @staticmethod
    @lru_cache(maxsize=1024)
    def get_bitcoin_price(date: float) -> Decimal:
        """Obtém o preço histórico do Bitcoin em USD para o
        timestamp especificado."""
        params = {
            "fsym": "BTC",
            "tsyms": "USD",
            "ts": date,
            "api_key": CRYPTOCOMPARE_API_KEY,
        }
        try:
            r = requests.get(CRYPTOCOMPARE_API_URL, params=params, timeout=10)
            r.raise_for_status()
            response = r.json()
            if response.get("Response", None):
                logger.error(f"Erro na CC API: {response}")
            price = r.json().get("BTC", {}).get("USD", 0)
            return Decimal(price)
        except requests.RequestException as e:
            logger.error(
                f"Erro ao pegar cotação do bitcoin para timestamp {date}: {e}"
            )
            raise e
