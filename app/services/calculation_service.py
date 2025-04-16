import logging
from datetime import datetime
from typing import Any, Collection

from flask_sqlalchemy import SQLAlchemy

from app.ext.models import Wallet
from app.ext.schemas import TransactionSchema, WalletSchema
from app.services.blockchain_service import BlockchainService
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)


class CalculationService:
    def __init__(self):
        self.blockchain = BlockchainService()
        self.prices = PriceService()
        self.tx_schema = TransactionSchema()
        self.wallet_schema = WalletSchema()

    @staticmethod
    def calculate_roa(invested_usd: float, balance_usd: float, returned_usd: float) -> float:
        if invested_usd > 0:
            roa = (balance_usd + returned_usd - invested_usd) / invested_usd * 100
            return roa
        else:
            logger.warning(f"ROA zerado: invested_usd = {invested_usd}")
            roa = 0
            return roa

    def calculate_btc_roa(self, btc_today: float, first_transaction_date: str) -> float:
        btc_before = self.prices.get_bitcoin_price(first_transaction_date)
        return (btc_today / btc_before) * 100

    def process_transaction(self, tx: dict[str, Any], address: str) -> dict[Any, Any]:
        try:
            tx_date = tx["status"]["block_time"]
            btc_price = self.prices.get_bitcoin_price(tx_date)

            total_received = 0
            total_spent = 0

            # Entradas: gastos (vin)
            for vin in tx.get("vin", []):
                prev = vin.get("prevout", {})
                if prev.get("scriptpubkey_address") == address:
                    total_spent += prev.get("value", 0) / 1e8

            # Saídas: recebimentos (vout)
            for vout in tx.get("vout", []):
                if vout.get("scriptpubkey_address") == address:
                    total_received += vout.get("value", 0) / 1e8

            net_btc = total_received - total_spent
            net_usd = net_btc * btc_price

            tx_in = True if net_btc >= 0 else False
            tx_date = datetime.fromtimestamp(tx_date).isoformat()
            return {
                "wallet_address": address,
                "transaction_date": tx_date,
                "balance_btc": net_btc,
                "balance_usd": net_usd,
                "tx_in": tx_in,
                "transaction_id": tx.get("txid"),
            }
        except Exception as e:
            logger.warning(
                f"Falha no processo a transação {tx.get('txid')} da carteira {address}: {e}"
            )
            return {}

    def calculate_wallet_data(  # noqa: PLR0914
        self, address: str
    ) -> tuple[dict[str, Any], list[dict[str, Any]]] | tuple[None, None]:
        wallet_info = self.blockchain.get_wallet_info(address)
        if not wallet_info:
            logger.error(f"Informações da Wallet não encontradas para atualizar {address}")

        txs = self.blockchain.get_all_transactions(address)
        if not txs:
            logger.error(f"Nenhuma transação encontrada para o endereço {address}")
            return None, None

        processed_txs = []
        invested_usd = 0
        returned_usd = 0

        # Data da primeira transação (mais antiga)
        first_tx_date = txs[-1]["status"]["block_time"]
        first_tx_date = datetime.fromtimestamp(first_tx_date).isoformat()
        # Processa apenas transações confirmadas
        for tx in txs:
            processed = self.process_transaction(tx, address)
            if not processed:
                continue
            processed_txs.append(processed)

            if processed["balance_btc"] > 0:
                invested_usd += abs(processed["balance_usd"])
            else:
                returned_usd += abs(processed["balance_usd"])

        wallet_tx_count = wallet_info.get("chain_stats", {}).get("tx_count", len(processed_txs))
        funded = wallet_info.get("chain_stats", {}).get("funded_txo_sum", 0) / 1e8
        spent = wallet_info.get("chain_stats", {}).get("spent_txo_sum", 0) / 1e8
        balance_btc = funded - spent

        current_price = self.prices.get_bitcoin_price(datetime.now())
        balance_usd = balance_btc * current_price

        roa = self.calculate_roa(invested_usd, balance_usd, returned_usd)
        btc_roa = self.calculate_btc_roa(current_price, first_tx_date)

        wallet_data = {
            "address": address,
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "transaction_count": wallet_tx_count,
            "btc_roa": btc_roa,
            "roa": roa,
            "first_transaction_date": first_tx_date,
        }
        return wallet_data, processed_txs

    def calculate_from_transactions(self, wallet: Wallet) -> dict[str, Any]:
        invested_usd = 0.0
        returned_usd = 0.0
        balance_btc = 0.0

        for tx in wallet.transactions:
            balance_btc += tx.balance_btc
            if tx.balance_btc > 0:
                invested_usd += abs(tx.balance_usd)
            else:
                returned_usd += abs(tx.balance_usd)

        current_price = self.prices.get_bitcoin_price(datetime.now().timestamp())
        logger.warning(f"Preço atual do BTC retornado como {current_price} para {wallet.address}")
        balance_usd = balance_btc * current_price

        roa = self.calculate_roa(invested_usd, balance_usd, returned_usd)
        btc_roa = self.calculate_btc_roa(current_price, wallet.first_transaction_date.timestamp())

        return {
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "btc_roa": btc_roa,
            "roa": roa,
        }

    def update_wallet(self, wallet: Wallet, db: SQLAlchemy) -> int | None:
        wallet_info = self.blockchain.get_wallet_info(wallet.address)
        if not wallet_info:
            logger.error(f"Informações da Wallet não encontradas para atualizar {wallet.address}")

        current_tx_count = wallet_info.get("chain_stats", {}).get("tx_count", None)
        has_new = current_tx_count > wallet.transaction_count

        wallet_data = self.calculate_from_transactions(wallet)
        wallet_data["transaction_count"] = current_tx_count
        new_txs_ids: Collection[int | None] = []

        if has_new:
            txs = self.blockchain.get_all_transactions(wallet.address)
            if not txs:
                return None

            stored_txids = {tx.transaction_id for tx in wallet.transactions}
            txs_ids = {tx.get("txid") for tx in txs}
            new_txs_ids = txs_ids.difference(stored_txids)
            processed_txs = [
                self.process_transaction(tx, wallet.address)
                for tx in txs
                if tx.get("txid") in new_txs_ids
            ]
            transactions = [self.tx_schema.load(tx, session=db.session) for tx in processed_txs]
            db.session.add_all(transactions)

        wallet = self.wallet_schema.load(
            wallet_data, instance=wallet, partial=True, session=db.session
        )
        try:
            db.session.commit()
            return len(new_txs_ids)
        except Exception as e:
            logger.error(f"Erro ao atualizar carteira {wallet.address}: {e}")
            db.session.rollback()
            return None
