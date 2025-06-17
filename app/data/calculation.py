from datetime import datetime
from decimal import Decimal
from typing import Any

import pytz
from loguru import logger

from app.data.schemas import TransactionSchema, WalletSchema
from app.external.apis.btc_exchange import PriceService


class Calculator:
    def __init__(self) -> None:
        self.prices = PriceService()
        self.tx_schema = TransactionSchema()
        self.schema = WalletSchema()
        self.timezone = pytz.timezone("America/Sao_Paulo")

    def calculate_btc_price_change(self, first_tx_dt: float) -> Decimal:
        """Calculate the percentage change in Bitcoin price"""
        btc_today = self.prices.get_bitcoin_price(
            datetime.now(tz=self.timezone)
        )
        btc_before = self.prices.get_bitcoin_price(first_tx_dt)
        if btc_before == 0:
            logger.warning("BTC price change zerado")
            return Decimal("0")
        return ((btc_today / btc_before) - 1) * 100

    @staticmethod
    def calculate_tx_total_spent(tx: dict[str, Any], address: str) -> Decimal:
        """Calculate the total amount spent in a transaction"""
        total_spent = Decimal("0")
        satoshi_to_btc = Decimal("1e8")
        for vin in tx.get("vin", []):
            prev = vin.get("prevout", {})
            if prev.get("scriptpubkey_address") == address:
                total_spent += (
                    Decimal(str(prev.get("value", 0))) / satoshi_to_btc
                )
        return total_spent

    @staticmethod
    def calculate_tx_total_received(
        tx: dict[str, Any], address: str
    ) -> Decimal:
        """Calculate the total amount received in a transaction"""
        total_received = Decimal("0")
        satoshi_to_btc = Decimal("1e8")
        for vout in tx.get("vout", []):
            if vout.get("scriptpubkey_address") == address:
                total_received += (
                    Decimal(str(vout.get("value", 0))) / satoshi_to_btc
                )
        return total_received

    @staticmethod
    def calculate_dietz(
        initial_value: Decimal,
        final_value: Decimal,
        invested: Decimal,
        returned: Decimal,
    ) -> Decimal:
        flux = invested - returned
        first_term = final_value - initial_value - flux
        second_term = initial_value + (flux / 2)
        return (first_term / second_term) * 100
