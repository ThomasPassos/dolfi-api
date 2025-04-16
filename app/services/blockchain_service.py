import os

import requests
from loguru import logger

BLOCKSTREAM_API_URL = os.getenv("BLOCKSTREAM_API_URL")


class BlockchainService:
    @staticmethod
    def get_wallet_info(address: str) -> dict[str, str] | None:
        logger.debug(f"Busca dos dados da carteira {address}")
        url = f"{BLOCKSTREAM_API_URL}/address/{address}"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error(f"Erro ao obter info da carteira {address}: {e}")
            return None

    @staticmethod
    def get_all_transactions(address: str) -> list[dict[str, str]]:
        logger.debug(f"Busca de todas as transações da carteira {address}")
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
                logger.debug(f"Fim da busca das transações para a carteira: {address}")
                break

            txs.extend(batch)
            last_txid = batch[-1]["txid"]
        return txs
