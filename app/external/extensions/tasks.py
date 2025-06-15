from decimal import Decimal
from typing import Any

from celery import chain, chord, group, shared_task
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.data.models import Wallet, db
from app.data.wallet import WalletGenerator

calc = WalletGenerator()


@shared_task
def update_all_wallets() -> dict[str, str]:
    logger.debug("Iniciando atualização de todas as carteiras")
    wallets = db.session.scalars(select(Wallet)).all()
    if wallets:
        wallets_to_update = set(filter(calc.has_new_txs, wallets))
        wallets_to_recalculate = set(wallets).difference(wallets_to_update)

        logger.debug(f"carteiras para atualizar: {wallets_to_update}")
        logger.debug(f"carteiras para recalcular: {wallets_to_recalculate}")

        addresses_to_update = [wallet.address for wallet in wallets_to_update]
        group(update_wallet.s(address) for address in addresses_to_update)()

        addresses_to_recalculate = [
            wallet.address for wallet in wallets_to_recalculate
        ]
        group(
            recalculate_wallet.s(address)
            for address in addresses_to_recalculate
        )()
        logger.info("Iniciada à atualização das carteiras")
        return {"message": "Iniciada à atualização das carteiras"}
    logger.warning("Nenhuma carteira foi retornada da base de dados")
    return {"message": "Nenhuma carteira para atualizar"}


@shared_task
def update_wallet(address: str) -> dict[str, str]:
    logger.info(f"Iniciando atualização da carteira {address}")
    try:
        chain(
            get_new_txs.s(address),
            start_processing.s(address=address),
            recalculate_wallet.si(address),
        )()
        logger.info(f"Atualização da carteira {address} iniciada")
        return {"message": f"Atualização da carteira {address} iniciada"}
    except Exception as e:
        logger.error(f"Falha ao atualizar carteira {address}: {e}")
        raise e


@shared_task
def start_processing(new_txs: list, address: str) -> dict[str, str] | None:
    try:
        logger.debug("Iniciando processamento das transações")
        chord(process_transaction.s(tx, address) for tx in new_txs)(
            load_new_txs.s(address)
        )
        return {"message": "Iniciado o processamento das txs"}
    except Exception as e:
        logger.error(f"Erro ao processar e inserir as transações: {e}")
        return None


@shared_task
def recalculate_wallet(address: str) -> dict[str, bool] | None:
    logger.debug(f"recalculando wallet {address}")
    wallet = db.session.get(Wallet, address)
    if wallet:
        wallet = calc.recalculate_wallet_data(wallet)
        logger.debug(f"recalculando wallet data {wallet}")
        try:
            db.session.commit()
            logger.debug(f"Dados calculados da wallet {wallet.address}")
            return {"sucess": True}
        except SQLAlchemyError:
            db.session.rollback()
            logger.debug(f"Falha ao calcular dados da wallet {wallet.address}")
            return {"sucess": False}
    raise Exception


@shared_task
def get_new_txs(address: str) -> list[dict[str, Any]] | dict[str, str]:
    logger.debug(f"pegando novas transações da wallet {address}")
    try:
        wallet = db.session.get(Wallet, address)
        if wallet:
            txs = calc.blockchain.get_all_transactions(wallet.address)
            stored_txids = {tx.transaction_id for tx in wallet.transactions}
            txs_ids = {tx.get("txid") for tx in txs}
            new_txs_ids = txs_ids.difference(stored_txids)
            new_txs = [tx for tx in txs if tx.get("txid") in new_txs_ids]
            logger.debug(
                f"Pegas as novas txs da wallet {address}: {len(new_txs)}"
            )
            return new_txs
        raise Exception
    except Exception:
        logger.error(f"Falha ao pegar as novas transações da wallet {address}")
        return {"message": "Falha ao pegar as novas transações"}


@shared_task
def load_new_txs(new_txs: list, address: str) -> None:
    logger.debug(
        f"Carregando na base de dados as novas transações: {len(new_txs)}"
    )
    wallet = db.session.get(Wallet, address)
    if wallet:
        wallet.transaction_count += len(new_txs)
        transactions = calc.txs_gen.schema.load(
            new_txs,
            session=db.session,  # type: ignore
            many=True,
        )
        try:
            db.session.add_all(transactions)
            db.session.commit()
            logger.debug(
                f"Carregadas na db as novas transações: {len(new_txs)}"
            )
        except Exception:
            db.session.rollback()
            logger.debug(
                f"Falha ao carregar as novas transações na db: {len(new_txs)}"
            )


@shared_task
def process_transaction(tx: dict[str, Any], address: str) -> dict[str, Any]:
    tx_date = int(tx["status"]["block_time"])
    btc_price = calc.prices.get_bitcoin_price(tx_date)

    total_received = Decimal("0")
    total_spent = Decimal("0")
    satoshi_to_btc = Decimal("1e8")

    for vin in tx.get("vin", []):
        prev = vin.get("prevout", {})
        if prev.get("scriptpubkey_address") == address:
            total_spent += Decimal(str(prev.get("value", 0))) / satoshi_to_btc

    for vout in tx.get("vout", []):
        if vout.get("scriptpubkey_address") == address:
            total_received += (
                Decimal(str(vout.get("value", 0))) / satoshi_to_btc
            )

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
