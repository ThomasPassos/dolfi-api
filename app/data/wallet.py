from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytz
from loguru import logger

from app.data.calculation import Calculator
from app.data.models import Transaction, Wallet
from app.data.schemas import WalletSchema
from app.data.tx import TxsGenerator
from app.external.apis.blockchain import BlockchainService
from app.external.apis.btc_exchange import PriceService


class WalletGenerator:
    def __init__(self) -> None:
        self.blockchain = BlockchainService()
        self.prices = PriceService()
        self.schema = WalletSchema()
        self.txs_gen = TxsGenerator()
        self.calc = Calculator()
        self.timezone = pytz.timezone("America/Sao_Paulo")

    def get_wallet_info(self, address: str) -> dict[str, Any] | None:
        """Get wallet info from the blockchain API"""
        wallet_info = self.blockchain.get_wallet_info(address)
        if not wallet_info:
            return None
        return wallet_info

    def has_new_txs(self, wallet: Wallet) -> bool:
        """Check if the wallet has new transactions"""
        wallet_info = self.get_wallet_info(wallet.address)
        if not wallet_info:
            return False
        current_tx_count = wallet_info.get("chain_stats", {}).get(
            "tx_count", None
        )
        has_new = current_tx_count > wallet.transaction_count
        return bool(has_new)

    def get_balance_usd(self, balance_btc: Decimal) -> Decimal:
        current_price = self.prices.get_bitcoin_price(
            datetime.now(tz=self.timezone).timestamp()
        )
        return balance_btc * current_price

    def generate_parcial_wallet(self, address: str) -> Wallet | None:
        logger.info(f"Iniciado extração de infos da wallet {address}")
        wallet_info = self.get_wallet_info(address)

        if not wallet_info:
            return None

        tx_count = wallet_info.get("chain_stats", {}).get("tx_count", 0)
        balance_btc = self.get_balance_btc(wallet_info)
        balance_usd = self.get_balance_usd(balance_btc)

        parcial_wallet = {
            "address": address,
            "balance_btc": balance_btc,
            "transaction_count": tx_count,
            "balance_usd": balance_usd,
        }
        return self.schema.load(parcial_wallet, transient=True)

    def complete_wallet(
        self, wallet: Wallet, txs: list[Transaction]
    ) -> Wallet:
        """Calcula dados da carteira e retorna junto
        com as transações processadas"""
        logger.debug(f"Completando wallet {wallet.address}")

        wallet.first_transaction_date = min(tx.transaction_date for tx in txs)
        invested, returned = self.calculate_invested_and_returned(txs)
        wallet.roa = self.calc.calculate_roa(
            invested, wallet.balance_usd, returned
        )
        wallet.btc_price_change = self.calc.calculate_btc_price_change(
            wallet.first_transaction_date  # type: ignore
        )

        logger.debug(f"Wallet {wallet.address} completada: {wallet}")
        return wallet

    def generate_wallet_and_txs(
        self, address: str
    ) -> tuple[Wallet, list[Transaction]]:
        wallet = self.generate_parcial_wallet(address)
        if not wallet:
            raise Exception

        txs = self.txs_gen.generate_transactions(address)
        complete_wallet = self.complete_wallet(wallet, txs)
        complete_txs = [
            self.txs_gen.complete_transaction(tx, wallet) for tx in txs
        ]
        return complete_wallet, complete_txs

    def recalculate_wallet_data(self, wallet: Wallet) -> Wallet:
        """Recalcula os dados da carteira com base nas
        transações e preços mais recentes"""
        balance_btc = Decimal("0")
        invested_usd = Decimal("0")
        returned_usd = Decimal("0")

        for tx in wallet.transactions:
            balance_btc += tx.balance_btc
            if tx.balance_btc > 0:
                invested_usd += abs(tx.balance_usd)
            else:
                returned_usd += abs(tx.balance_usd)

        wallet.balance_btc = balance_btc
        wallet.balance_usd = self.get_balance_usd(balance_btc)
        wallet.roa = self.calc.calculate_roa(
            invested_usd, wallet.balance_usd, returned_usd
        )
        wallet.btc_price_change = self.calc.calculate_btc_price_change(
            wallet.first_transaction_date.timestamp()
        )
        wallet.transaction_count = len(wallet.transactions)
        return wallet

    @staticmethod
    def get_balance_btc(
        wallet_info: dict[str, Any],
    ) -> Decimal:
        """Get wallet balances and current price of Bitcoin"""
        satoshi_to_btc = Decimal("1e8")
        funded = (
            Decimal(
                str(
                    wallet_info.get("chain_stats", {}).get("funded_txo_sum", 0)
                )
            )
            / satoshi_to_btc
        )
        spent = (
            Decimal(
                str(wallet_info.get("chain_stats", {}).get("spent_txo_sum", 0))
            )
            / satoshi_to_btc
        )
        return funded - spent

    @staticmethod
    def calculate_invested_and_returned(
        txs: list[Transaction] | Sequence[Transaction],
    ) -> tuple[Decimal, Decimal]:
        invested_usd = Decimal("0")
        returned_usd = Decimal("0")

        for tx in txs:
            if tx.balance_btc > 0:
                invested_usd += abs(tx.balance_usd)
            else:
                returned_usd += abs(tx.balance_usd)
        return invested_usd, returned_usd
