import logging
import os

import requests

BLOCKSTREAM_API_URL = os.environ.get("BLOCKSTREAM_API_URL")
logger = logging.getLogger(__name__)


class BlockchainService:
    @staticmethod
    def get_wallet_info(address):
        url = f"{BLOCKSTREAM_API_URL}/address/{address}"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error(f"Erro ao obter info da carteira {address}: {e}")
            return None

    @staticmethod
    def get_all_transactions(address):
        txs = []
        last_txid = None
        while True:
            url = f"{BLOCKSTREAM_API_URL}/address/{address}/txs/chain"
            if last_txid:
                url += f"/{last_txid}"

            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                batch = r.json()
            except requests.RequestException as e:
                logger.error(f"Erro ao obter transações para a carteira {address}: {e}")
                break

            if not batch:
                break

            txs.extend(batch)

            # Se o lote for menor que 25, consideramos que é a última página.
            if len(batch) < 25:
                break

            last_txid = batch[-1]["txid"]
        return txs
