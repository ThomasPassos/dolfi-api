from datetime import datetime
from decimal import Decimal
from typing import Any, Collection, Union

from flask_sqlalchemy import SQLAlchemy
from loguru import logger

from app.external.models import Wallet
from app.external.schemas import TransactionSchema, WalletSchema
from app.services.blockchain_service import BlockchainService
from app.services.price_service import PriceService


class DolfiCalculator:
    def __init__(self):
        self.blockchain = BlockchainService()
        self.prices = PriceService()
        self.tx_schema = TransactionSchema()
        self.wallet_schema = WalletSchema()

    def get_wallet_info(self, address: str) -> dict[str, Any] | None:
        """Get wallet info from the blockchain API"""
        wallet_info = self.blockchain.get_wallet_info(address)
        if not wallet_info:
            return None
        return wallet_info

    def get_txs(self, address: str) -> list[dict[str, Any]] | None:
        """Get all transactions from the blockchain API"""
        txs = self.blockchain.get_all_transactions(address)
        if not txs:
            return None
        return txs

    def has_new_txs(self, wallet: Wallet) -> bool:
        """Check if the wallet has new transactions"""
        try:
            wallet_info = self.get_wallet_info(wallet.address)
            current_tx_count = wallet_info.get("chain_stats", {}).get("tx_count", None)
            has_new = current_tx_count > wallet.transaction_count
            if has_new:
                return True
            return False
        except Exception:
            return False

    def calculate_btc_price_change(self, btc_today: Decimal, first_tx_dt: Union[int, float]) -> Decimal:
        """Calculate the percentage change in Bitcoin price"""
        btc_before = self.prices.get_bitcoin_price(first_tx_dt)
        if btc_before == 0:
            logger.warning("BTC price change zerado")
            return Decimal("0")
        return ((btc_today / btc_before) - 1) * 100

    @staticmethod
    def calculate_roa(invested_usd: Decimal, balance_usd: Decimal, returned_usd: Decimal) -> Decimal:
        """'Calculate the Return on Assets (ROA)"""
        if invested_usd > 0:
            roa = (balance_usd + returned_usd - invested_usd) / invested_usd * 100
            return roa
        logger.warning(f"ROA zerado: invested_usd = {invested_usd}")
        return Decimal("0")

    @staticmethod
    def calculate_tx_total_spent(tx: dict[str, Any], address: str) -> Decimal:
        '''Calculate the total amount spent in a transaction'''
        total_spent = Decimal("0")
        satoshi_to_btc = Decimal("1e8")
        for vin in tx.get("vin", []):
            prev = vin.get("prevout", {})
            if prev.get("scriptpubkey_address") == address:
                total_spent += Decimal(str(prev.get("value", 0))) / satoshi_to_btc
        return total_spent

    @staticmethod
    def calculate_tx_total_received(tx: dict[str, Any], address: str) -> Decimal:
        '''Calculate the total amount received in a transaction'''
        total_received = Decimal("0")
        satoshi_to_btc = Decimal("1e8")
        for vout in tx.get("vout", []):
            if vout.get("scriptpubkey_address") == address:
                total_received += Decimal(str(vout.get("value", 0))) / satoshi_to_btc
        return total_received

    def process_transaction(self, tx: dict[str, Any], address: str) -> dict[str, Any] | None:
        """Process a transaction and return relevant data (incoming/outgoing, balance, etc)"""
        try:
            tx_date = int(tx["status"]["block_time"])
            btc_price = self.prices.get_bitcoin_price(tx_date)

            total_received = self.calculate_tx_total_received(tx, address)
            total_spent = self.calculate_tx_total_spent(tx, address)

            net_btc = total_received - total_spent
            net_usd = net_btc * btc_price

            is_incoming = net_btc >= 0
            return {
                "wallet_address": address,
                "transaction_date": tx_date,
                "balance_btc": net_btc,
                "balance_usd": net_usd,
                "is_incoming": is_incoming,
                "transaction_id": tx.get("txid"),
            }
        except Exception as e:
            logger.error(f"Erro no processamento da transação {tx.get('txid')} da carteira {address}: {e}")
            return None

    def process_all_transactions(self, txs: list[dict[str, Any]], address: str) -> tuple[Decimal, Decimal, list[dict[str, Any]]]:
        ''''Process all transactions and return invested and returned USD amounts, along with processed transactions'''
        processed_txs = []
        invested_usd = Decimal("0")
        returned_usd = Decimal("0")

        for tx in txs:
            processed = self.process_transaction(tx, address)
            if not processed:
                continue
            processed_txs.append(processed)

            balance_btc = Decimal(str(processed["balance_btc"]))
            balance_usd = Decimal(str(processed["balance_usd"]))
            if balance_btc > 0:
                invested_usd += abs(balance_usd)
            else:
                returned_usd += abs(balance_usd)
        return invested_usd, returned_usd, processed_txs

    @staticmethod
    def get_balances(wallet_info: dict[str, Any], current_price: Decimal) -> tuple[Decimal, Decimal]:
        '''Get wallet balances and current price of Bitcoin'''
        satoshi_to_btc = Decimal("1e8")
        funded = Decimal(str(wallet_info.get("chain_stats", {}).get("funded_txo_sum", 0))) / satoshi_to_btc
        spent = Decimal(str(wallet_info.get("chain_stats", {}).get("spent_txo_sum", 0))) / satoshi_to_btc

        balance_btc = funded - spent
        balance_usd = balance_btc * current_price
        return balance_btc, balance_usd

    def calculate_wallet_data(self, address: str) -> tuple[dict[str, Any], list[dict[str, Any]]] | tuple[None, None]:
        '''Calculate wallet data and return it along with processed transactions'''
        logger.info(f"Iniciado processo de extração de dados da wallet {address}")
        wallet_info = self.get_wallet_info(address)
        txs = self.get_txs(address)
        if not wallet_info or not txs:
            return None, None

        logger.debug(f"Iniciando processamento dos dados da wallet {address}")
        first_tx_date = int(txs[-1]["status"]["block_time"])
        invested_usd, returned_usd, processed_txs = self.process_all_transactions(txs, address)
        logger.debug(f"Txs da wallet {address} processadas: {invested_usd, returned_usd}")

        wallet_tx_count = wallet_info.get("chain_stats", {}).get("tx_count", len(processed_txs))
        current_price = self.prices.get_bitcoin_price(datetime.now().timestamp())
        balance_btc, balance_usd = self.get_balances(wallet_info, current_price)
        roa = self.calculate_roa(invested_usd, balance_usd, returned_usd)
        btc_price_change = self.calculate_btc_price_change(current_price, first_tx_date)

        wallet_data = {
            "address": address,
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "transaction_count": wallet_tx_count,
            "btc_price_change": btc_price_change,
            "roa": roa,
            "first_transaction_date": first_tx_date,
        }
        logger.debug(f"Dados da wallet {address} processados: {wallet_data}")
        return wallet_data, processed_txs

    def recalculate_wallete_data(self, wallet: Wallet) -> dict[str, Any]:
        '''Recalculate wallet data based on the latest transactions and prices'''
        invested_usd = Decimal("0")
        returned_usd = Decimal("0")
        balance_btc = Decimal("0")

        for tx in wallet.transactions:
            balance_btc += tx.balance_btc
            if tx.balance_btc > 0:
                invested_usd += abs(tx.balance_usd)
            else:
                returned_usd += abs(tx.balance_usd)

        current_price = self.prices.get_bitcoin_price(datetime.now().timestamp())
        balance_usd = balance_btc * current_price
        roa = self.calculate_roa(invested_usd, balance_usd, returned_usd)
        btc_price_change = self.calculate_btc_price_change(current_price, wallet.first_transaction_date.timestamp())

        return {
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "btc_price_change": btc_price_change,
            "roa": roa,
            "transaction_count": len(wallet.transactions),
        }
