from datetime import datetime
from decimal import Decimal
from typing import Any, Collection, Union

from flask_sqlalchemy import SQLAlchemy
from loguru import logger

from app.ext.models import Wallet
from app.ext.schemas import TransactionSchema, WalletSchema
from app.services.blockchain_service import BlockchainService
from app.services.price_service import PriceService


class CalculationService:
    def __init__(self):
        self.blockchain = BlockchainService()
        self.prices = PriceService()
        self.tx_schema = TransactionSchema()
        self.wallet_schema = WalletSchema()

    @staticmethod
    def calculate_roa(invested_usd: Decimal, balance_usd: Decimal, returned_usd: Decimal) -> Decimal:
        if invested_usd > 0:
            roa = (balance_usd + returned_usd - invested_usd) / invested_usd * 100
            return roa
        logger.warning(f"ROA zerado: invested_usd = {invested_usd}")
        return Decimal("0")

    def calculate_btc_price_change(self, btc_today: Decimal, first_tx_dt: Union[int, float]) -> Decimal:
        btc_before = Decimal(str(self.prices.get_bitcoin_price(first_tx_dt)))
        if btc_before == 0:
            logger.warning("BTC price change zerado")
            return Decimal("0")
        return ((btc_today / btc_before) - 1) * 100

    def process_transaction(self, tx: dict[str, Any], address: str) -> dict[Any, Any]:
        try:
            tx_date = tx["status"]["block_time"]
            btc_price = Decimal(str(self.prices.get_bitcoin_price(int(tx_date))))

            total_received = Decimal("0")
            total_spent = Decimal("0")
            satoshi_to_btc = Decimal("1e8")

            for vin in tx.get("vin", []):
                prev = vin.get("prevout", {})
                if prev.get("scriptpubkey_address") == address:
                    total_spent += Decimal(str(prev.get("value", 0))) / satoshi_to_btc

            for vout in tx.get("vout", []):
                if vout.get("scriptpubkey_address") == address:
                    total_received += Decimal(str(vout.get("value", 0))) / satoshi_to_btc

            net_btc = total_received - total_spent
            net_usd = net_btc * btc_price

            is_incoming = net_btc >= 0
            tx_date = datetime.fromtimestamp(tx_date).isoformat()
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
            return {"error": str(e)}

    def calculate_wallet_data(self, address: str) -> tuple[dict[str, Any], list[dict[str, Any]]] | tuple[None, None]:  # noqa: PLR0914
        logger.info(f"Iniciado processo de extração de dados da wallet {address}")

        wallet_info = self.blockchain.get_wallet_info(address)
        if not wallet_info:
            return None, None

        txs = self.blockchain.get_all_transactions(address)
        if not txs:
            logger.error(f"Nenhuma tx encontrada para o endereço {address}")
            return None, None

        logger.debug(f"Iniciando processamento dos dados da wallet {address}")
        processed_txs = []
        invested_usd = Decimal("0")
        returned_usd = Decimal("0")

        first_tx_date = txs[-1]["status"]["block_time"]
        first_tx_date_formatted = datetime.fromtimestamp(first_tx_date).isoformat()

        for tx in txs:
            processed = self.process_transaction(tx, address)
            if not processed or "error" in processed:
                continue
            processed_txs.append(processed)

            balance_btc = Decimal(str(processed["balance_btc"]))
            balance_usd = Decimal(str(processed["balance_usd"]))
            if balance_btc > 0:
                invested_usd += abs(balance_usd)
            else:
                returned_usd += abs(balance_usd)
        logger.debug(f"Txs da wallet {address} processados: {processed_txs[0] if processed_txs else 'nenhuma'}")

        wallet_tx_count = wallet_info.get("chain_stats", {}).get("tx_count", len(processed_txs))
        funded = Decimal(str(wallet_info.get("chain_stats", {}).get("funded_txo_sum", 0))) / Decimal("1e8")
        spent = Decimal(str(wallet_info.get("chain_stats", {}).get("spent_txo_sum", 0))) / Decimal("1e8")
        balance_btc = funded - spent

        current_price = Decimal(str(self.prices.get_bitcoin_price(datetime.now().timestamp())))
        balance_usd = balance_btc * current_price

        roa = self.calculate_roa(invested_usd, balance_usd, returned_usd)
        btc_price_change = self.calculate_btc_price_change(current_price, int(first_tx_date))

        wallet_data = {
            "address": address,
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "transaction_count": wallet_tx_count,
            "btc_price_change": btc_price_change,
            "roa": roa,
            "first_transaction_date": first_tx_date_formatted,
        }
        logger.debug(f"Dados da wallet {address} processados: {wallet_data}")
        return wallet_data, processed_txs

    def calculate_from_transactions(self, wallet: Wallet) -> dict[str, Any]:
        invested_usd = Decimal("0")
        returned_usd = Decimal("0")
        balance_btc = Decimal("0")

        for tx in wallet.transactions:
            tx_btc = Decimal(str(tx.balance_btc))
            tx_usd = Decimal(str(tx.balance_usd))
            balance_btc += tx_btc
            if tx_btc > 0:
                invested_usd += abs(tx_usd)
            else:
                returned_usd += abs(tx_usd)

        current_price = Decimal(str(self.prices.get_bitcoin_price(datetime.now().timestamp())))
        balance_usd = balance_btc * current_price

        roa = self.calculate_roa(invested_usd, balance_usd, returned_usd)
        btc_price_change = self.calculate_btc_price_change(current_price, wallet.first_transaction_date.timestamp())
        return {
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "btc_price_change": btc_price_change,
            "roa": roa,
        }

    def update_wallet(self, wallet: Wallet, db: SQLAlchemy) -> int | None:
        wallet_info = self.blockchain.get_wallet_info(wallet.address)
        if not wallet_info:
            return None

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
            processed_txs = [self.process_transaction(tx, wallet.address) for tx in txs if tx.get("txid") in new_txs_ids]
            transactions = [self.tx_schema.load(tx, session=db.session) for tx in processed_txs if "error" not in tx]
            db.session.add_all(transactions)
            logger.debug(f"Txs da wallet {wallet.address} processadas, Ex: {transactions[0] if transactions else 'nenhuma'}")

        wallet = self.wallet_schema.load(wallet_data, instance=wallet, partial=True, session=db.session)
        logger.debug(f"Dados calculados da wallet {wallet.address}: {wallet}")

        try:
            db.session.commit()
            return len(new_txs_ids)
        except Exception as e:
            logger.error(f"Erro ao atualizar wallet {wallet.address}: {e}")
            db.session.rollback()
            return None
