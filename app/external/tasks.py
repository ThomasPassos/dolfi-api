from datetime import datetime
from decimal import Decimal
from typing import Any

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
def insert_data_in_db(*args) -> dict[str, Any]:
    logger.info(f"{args}")
    wallet_data = args[0][0]
    txs = args[0][1]
    wallet = calc.wallet_schema.load(wallet_data, session=db.session)
    transactions = calc.tx_schema.load(txs, session=db.session, many=True)
    try:
        db.session.add(wallet)
        db.session.add_all(transactions)
        db.session.commit()
        return {"sucess": True}
    except SQLAlchemyError as e:
        db.session.rollback()
        return {"sucess": False, "error": e}


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


@shared_task
def calculate_wallet_data(txs: list, wallet_info: dict):
    invested_usd = Decimal("0")
    returned_usd = Decimal("0")
    for tx in txs:
        balance_btc = tx["balance_btc"]
        balance_usd = tx["balance_usd"]
        if balance_btc > 0:
            invested_usd += abs(balance_usd)
        else:
            returned_usd += abs(balance_usd)
    sorted_txs = sorted(txs, key=lambda x: x["transaction_date"])
    first_tx_date = sorted_txs[-1]["transaction_date"]
    tx_count = wallet_info.get("chain_stats", {}).get("tx_count", len(txs))

    funded = Decimal(str(wallet_info.get("chain_stats", {}).get("funded_txo_sum", 0))) / Decimal("1e8")
    spent = Decimal(str(wallet_info.get("chain_stats", {}).get("spent_txo_sum", 0))) / Decimal("1e8")
    balance_btc = funded - spent
    current_price = Decimal(str(calc.prices.get_bitcoin_price(datetime.now().timestamp())))
    balance_usd = balance_btc * current_price
    roa = calc.calculate_roa(invested_usd, balance_usd, returned_usd)
    btc_price_change = calc.calculate_btc_price_change(current_price, first_tx_date)
    return {
        "address": wallet_info.get("address"),
        "balance_btc": balance_btc,
        "balance_usd": balance_usd,
        "transaction_count": tx_count,
        "btc_price_change": btc_price_change,
        "roa": roa,
        "first_transaction_date": first_tx_date,
    }, txs
