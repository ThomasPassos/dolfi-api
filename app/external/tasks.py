from decimal import Decimal

from celery import chain, group, shared_task
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.external.models import Wallet, db
from app.services.calculation_service import DolfiCalculator

calc = DolfiCalculator()


@shared_task
def update_all_wallets():
    wallets = db.session.execute(select(Wallet)).scalars().all()
    if wallets:
        wallets_to_update = filter(calc.has_new_txs, wallets)
        addresses_to_update = [wallet.address for wallet in wallets_to_update]
        results = group(update_wallet.s(address) for address in addresses_to_update)()
        print(results)
        wallets_to_recalculate = filter(lambda x: False if calc.has_new_txs(x) else True, wallets)
        addresses_to_recalculate = [wallet.address for wallet in wallets_to_recalculate]
        results_2 = group(recalculate_wallet.s(address) for address in addresses_to_recalculate)()
        print(results_2)
        return {"message": "Iniciada à atualização das carteiras"}
    logger.warning("Nenhuma carteira foi retornada da base de dados")
    return {"message": "Nenhuma carteira para atualizar"}


@shared_task
def update_wallet(address: str):
    try:
        chain(get_new_txs.s(address), process_transaction.map(), load_new_txs.s(), recalculate_wallet.si(address))()
        return {"message": f"Atualização da carteira {address} iniciada"}
    except Exception as e:
        logger.error(f"Falha ao atualizar carteira {address}: {e}")
        raise Exception
        # return {"message": f"falha ao iniciar atualização da carteira {address}"}


@shared_task
def recalculate_wallet(address: str):
    wallet = db.session.get(Wallet, address)
    wallet_data = calc.calculate_from_transactions(wallet)
    wallet = calc.wallet_schema.load(wallet_data, instance=wallet, partial=True, session=db.session)
    try:
        db.session.commit()
        logger.debug(f"Dados calculados da wallet {wallet.address}: {wallet}")
        return {"sucess": True}
    except SQLAlchemyError:
        db.session.rollback()
        logger.debug(f"Falha ao calcular dados da wallet {wallet.address}: {wallet}")
        return {"sucess": False}


@shared_task
def get_new_txs(address: str):
    try:
        wallet = db.session.get(Wallet, address)
        txs = calc.blockchain.get_all_transactions(wallet.address)
        stored_txids = {tx.transaction_id for tx in wallet.transactions}
        txs_ids = {tx.get("txid") for tx in txs}
        new_txs_ids = txs_ids.difference(stored_txids)
        new_txs = [tx for tx in txs if tx.get("txid") in new_txs_ids]
        return new_txs
    except Exception:
        logger.error(f"Falha ao pegar as novas transações da wallet {address}")
        return {"message": "Falha ao pegar as novas transações"}


@shared_task
def load_new_txs(new_txs: list):
    transactions = calc.tx_schema.load(new_txs, session=db.session, many=True)
    try:
        db.session.add_all(transactions)
        db.session.commit()
    except Exception:
        db.session.rollback()


@shared_task
def process_transaction(tx, address) -> dict:
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
            total_received += Decimal(str(vout.get("value", 0))) / satoshi_to_btc

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
