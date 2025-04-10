import logging
from datetime import datetime
from typing import Any

from app import db
from app.models import Transaction, Wallet
from app.services.blockchain_service import BlockchainService
from app.services.price_service import PriceService

logger = logging.getLogger(__name__)


class CalculationService:
    def __init__(self):
        self.blockchain = BlockchainService()
        self.prices = PriceService()

    def process_transaction(self, tx: dict[str:Any], address: str) -> dict[str:Any]:
        try:
            tx_date = datetime.fromtimestamp(tx["status"]["block_time"])
        except Exception as e:
            logger.error(f"Erro ao converter block_time para datetime: {e}")
            tx_date = datetime.now()

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

        return {
            "transaction_date": tx_date,
            "balance_btc": net_btc,
            "balance_usd": net_usd,
            "tx_in": tx_in,
            "txid": tx.get("txid"),
        }

    def calculate_wallet_data(self, address: str) -> tuple[dict[str], list[dict[str:Any]]]:
        wallet_info = self.blockchain.get_wallet_info(address)
        if not wallet_info:
            logger.error(f"Informações da Wallet não encontradas para o endereço {address}")
            return None, None

        txs = self.blockchain.get_all_transactions(address)
        if not txs:
            logger.error(f"Nenhuma transação encontrada para o endereço {address}")
            return None, None

        processed_txs = []
        invested_usd = 0
        returned_usd = 0

        # Data da primeira transação (mais antiga)
        first_tx_date = datetime.fromtimestamp(txs[-1]["status"]["block_time"]) if txs else None

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

        # Cálculo do ROA: se invested_usd > 0, senão ROA=0 para evitar divisão por zero
        if invested_usd > 0:
            roa = (balance_usd + returned_usd - invested_usd) / invested_usd * 100
        else:
            roa = 0
            logger.warning(f"ROA zerado: invested_usd = {invested_usd}")

        wallet_data = {
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "transaction_count": wallet_tx_count,
            "roa": roa,
            "first_transaction_date": first_tx_date,
        }
        return wallet_data, processed_txs

    def calculate_from_transactions(self, wallet: Wallet):
        invested_usd = 0
        returned_usd = 0
        balance_btc = 0

        for tx in wallet.transactions:
            balance_btc += tx.balance_btc
            if tx.balance_btc > 0:
                invested_usd += abs(tx.balance_usd)
            else:
                returned_usd += abs(tx.balance_usd)

        current_price = self.prices.get_bitcoin_price(datetime.now())
        logger.warning(f"Preço atual do BTC retornado como {current_price} para {wallet.address}")
        balance_usd = balance_btc * current_price

        if invested_usd > 0:
            roa = (balance_usd + returned_usd - invested_usd) / invested_usd * 100
        else:
            roa = 0
            logger.warning(f"ROA zerado: invested_usd = {invested_usd}")

        return {
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "roa": roa,
        }

    def update_wallet(self, wallet: Wallet):
        wallet_info = self.blockchain.get_wallet_info(wallet.address)
        if not wallet_info:
            logger.error(f"Informações da Wallet não encontradas para atualizar {wallet.address}")
            return

        current_tx_count = wallet_info.get("chain_stats", {}).get("tx_count", None)
        has_new = current_tx_count > wallet.transaction_count

        if has_new:
            txs = self.blockchain.get_all_transactions(wallet.address)
            if not txs:
                logger.error(f"Nenhuma transação encontrada para {wallet.address}")
                return

            processed_txs = []
            stored_txids = {tx.transaction_id for tx in wallet.transactions}

            for tx in txs:
                processed = self.process_transaction(tx, wallet.address)
                if not processed:
                    continue
                processed_txs.append(processed)
                if processed["txid"] not in stored_txids:
                    transaction = Transaction(
                        transaction_id=processed["txid"],
                        wallet_address=wallet.address,
                        transaction_date=processed["transaction_date"],
                        balance_btc=processed["balance_btc"],
                        balance_usd=processed["balance_usd"],
                        tx_in=processed["tx_in"],
                    )
                    db.session.add(transaction)

            if current_tx_count is None:
                current_tx_count = len(wallet.transactions)

            wallet_data = self.calculate_from_transactions(wallet)
            wallet.balance_btc = wallet_data["balance_btc"]
            wallet.balance_usd = wallet_data["balance_usd"]
            wallet.roa = wallet_data["roa"]
            wallet.transaction_count = current_tx_count

        else:
            wallet_data = self.calculate_from_transactions(wallet)
            wallet.balance_usd = wallet_data["balance_usd"]
            wallet.roa = wallet_data["roa"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao atualizar carteira {wallet.address}: {e}")
            db.session.rollback()
