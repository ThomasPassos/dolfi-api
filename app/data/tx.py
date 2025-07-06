from typing import Any

import pytz
from loguru import logger

from app.data.calculation import Calculator
from app.data.models import Transaction, Wallet
from app.data.schemas import TransactionSchema
from app.external.apis.blockchain import BlockchainService
from app.external.apis.btc_exchange import PriceService


class TxsGenerator:
    def __init__(self) -> None:
        self.prices = PriceService()
        self.blockchain = BlockchainService()
        self.schema = TransactionSchema()
        self.calc = Calculator()
        self.timezone = pytz.timezone("America/Sao_Paulo")

    def get_txs(self, address: str) -> list[dict[str, Any]] | None:
        """Get all transactions from the blockchain API"""
        txs = self.blockchain.get_all_transactions(address)
        if not txs:
            return None
        return txs

    def process_transaction(
        self, tx: dict[str, Any], address: str
    ) -> Transaction | None:
        """Process a transaction and return relevant data
        (incoming/outgoing, balance, etc)"""
        try:
            tx_date = int(tx["status"]["block_time"])
            btc_price = self.prices.get_bitcoin_price(tx_date)

            total_received = self.calc.calculate_tx_total_received(tx, address)
            total_spent = self.calc.calculate_tx_total_spent(tx, address)

            net_btc = total_received - total_spent
            net_usd = net_btc * btc_price

            is_incoming = net_btc >= 0
            tx_raw = {
                "wallet_address": address,
                "transaction_date": tx_date,
                "balance_btc": net_btc,
                "balance_usd": net_usd,
                "is_incoming": is_incoming,
                "transaction_id": tx.get("txid"),
            }
            return self.schema.load(tx_raw, transient=True)
        except Exception as e:
            logger.error(
                f"""Erro no processamento da transação {tx.get("txid")}
                da carteira {address}: {e}"""
            )
            return None

    def generate_transactions(self, address: str) -> list[Transaction]:
        txs = self.get_txs(address)
        """Process all transactions and return invested and returned USD
        amounts, along with processed transactions"""
        return [self.process_transaction(tx, address) for tx in txs if tx]  # type: ignore

    @staticmethod
    def complete_transaction(tx: Transaction, wallet: Wallet) -> Transaction:
        tx.percent_from_wallet = 10
        return tx
