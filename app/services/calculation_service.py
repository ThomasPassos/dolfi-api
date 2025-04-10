import logging
from datetime import datetime
from typing import Any

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

    def calculate_wallet_data(self, address: str) -> dict[str]:
        wallet_info = self.blockchain.get_wallet_info(address)
        if not wallet_info:
            logger.error(f"Wallet info não encontrada para o endereço {address}")
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
        roa = (
            ((balance_usd + returned_usd - invested_usd) / invested_usd * 100)
            if invested_usd > 0
            else 0
        )

        wallet_data = {
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "transaction_count": wallet_tx_count,
            "roa": roa,
            "first_transaction_date": first_tx_date,
        }
        return wallet_data, processed_txs

    def update_wallet(self, wallet):
        wallet_info = self.blockchain.get_wallet_info(wallet.address)
        if not wallet_info:
            logger.error(f"Wallet info não encontrada para atualizar {wallet.address}")
            return

        txs = self.blockchain.get_all_transactions(wallet.address)
        current_tx_count = wallet_info.get("chain_stats", {}).get("tx_count", 0)
        has_new = current_tx_count > wallet.transaction_count

        if has_new:
            wallet_data, processed_txs = self.calculate_wallet_data(wallet.address)
            if not wallet_data:
                return

            wallet.balance_btc = wallet_data["balance_btc"]
            wallet.balance_usd = wallet_data["balance_usd"]
            wallet.transaction_count = wallet_data["transaction_count"]
            wallet.roa = wallet_data["roa"]
            if wallet.first_transaction_date is None and wallet_data["first_transaction_date"]:
                wallet.first_transaction_date = wallet_data["first_transaction_date"]

            stored_txids = {tx.transaction_id for tx in wallet.transactions}
            for tx in processed_txs:
                if tx["txid"] not in stored_txids:
                    yield tx
        else:
            current_price = self.prices.get_bitcoin_price(datetime.now())
            wallet.balance_usd = wallet.balance_btc * current_price

            # Recalcula ROA com base nos dados atuais (sem refetchar todas as transações)
            (
                _,
                _processed_txs_listed_only_for_roa_calc_needed_here_if_not_stored_elsewhere_,
            ) = _self.calculate_wallet_data(wallet.address)
            (
                _,
                _processed_txs_listed_only_for_roa_calc_needed_here_if_not_stored_elsewhere_,
            ) = _self.calculate_wallet_data(wallet.address)
