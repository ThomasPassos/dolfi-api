from datetime import datetime
from decimal import Decimal

from celery import chord, group, shared_task
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.external.models import Wallet, db
from app.services.calculation_service import DolfiCalculator

calc = DolfiCalculator()


@shared_task(bind=True, max_retries=1)
def update_wallets(self):
    try:
        wallets = db.session.execute(select(Wallet)).scalars().all()
        if wallets:
            wallets_to_update = group(update_wallet.s(wallet) for wallet in wallets)
            wallets_to_update.delay()
        else:
            logger.warning("Nenhuma carteira foi retornada da base de dados")
    except Exception as e:
        raise self.retry(exc=e, countdown=20)


@shared_task(bind=True, max_retries=5)
def update_wallet(self, wallet: Wallet):
    try:
        logger.info(f"Atualizando carteira {wallet.address}!")
        logger.info(f"Carteira {wallet.address} atualizada!")
    except Exception as e:
        raise self.retry(exc=e, countdown=5)


@shared_task(bind=True, max_retries=5)
def insert_wallet(self, address: str) -> None:
    try:
        info = calc.get_wallet_info(address)
        txs = calc.get_txs(address)
        info = self.blockchain.get_wallet_info(address)
        txs = self.blockchain.get_all_transactions(address)
        data_chord = chord((process_transaction.s(tx, address) for tx in txs), calculate_wallet_data.s(wallet_info=info)).get()
        wallet_data, txs = data_chord
        wallet = calc.wallet_schema.load(wallet_data, session=db.session)

        try:
            db.session.add(wallet)
            db.session.add_all(txs)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()

    except Exception as e:
        raise self.retry(exc=e, countdown=20)


@shared_task(bind=True, max_retries=10)
def process_transaction(self, tx, address) -> dict:
    try:
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
    except Exception as e:
        raise self.retry(exc=e, countdown=5)


@shared_task(bind=True, max_retries=10)
def calculate_wallet_data(self, wallet_info: dict, txs: list):
    try:
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

        wallet_data = {
            "address": wallet_info.address,
            "balance_btc": balance_btc,
            "balance_usd": balance_usd,
            "transaction_count": tx_count,
            "btc_price_change": btc_price_change,
            "roa": roa,
            "first_transaction_date": first_tx_date,
        }
        return wallet_data, txs
    except Exception as e:
        raise self.retry(exc=e, countdown=5)
