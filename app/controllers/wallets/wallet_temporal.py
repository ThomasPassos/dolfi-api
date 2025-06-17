from datetime import datetime, timedelta

import pytz
from flask_sqlalchemy import SQLAlchemy

from app.data.models import Wallet
from app.data.schemas import WalletSchema
from app.data.wallet import WalletGenerator
from app.external.apis.btc_exchange import PriceService


class WalletTemporalController:
    def __init__(self, db: SQLAlchemy) -> None:
        self.db = db
        self.tz = pytz.timezone("America/Sao_Paulo")
        self.wallet_gen = WalletGenerator()
        self.schema = WalletSchema()
        self.price = PriceService()

    def find_wallet(self, address: str) -> Wallet | None:
        return self.db.session.get(Wallet, address)

    def generate_temporal_wallet(self, wallet: Wallet, days: int) -> Wallet:
        date = self.calculate_date(days)

        before_txs = [
            tx for tx in wallet.transactions if tx.transaction_date <= date
        ]
        after_txs = [
            tx for tx in wallet.transactions if tx.transaction_date > date
        ]
        invested, returned = self.wallet_gen.calculate_invested_and_returned(
            after_txs
        )

        past_balance_btc = sum(tx.balance_btc for tx in before_txs)
        past_balance_price = self.price.get_bitcoin_price(date.timestamp())
        initial_value = past_balance_price * past_balance_btc

        roa = self.wallet_gen.calc.calculate_dietz(
            initial_value,
            wallet.balance_usd,  # type: ignore
            invested,
            returned,
        )
        txs_count = len(after_txs)
        btc_price_change = self.wallet_gen.calc.calculate_btc_price_change(
            date.timestamp()
        )

        parcial_wallet = {
            "address": wallet.address,
            "transaction_count": txs_count,
            "roa": roa,
            "btc_price_change": btc_price_change,
        }
        return self.schema.load(parcial_wallet, transient=True)

    def calculate_date(self, days: int) -> datetime:
        today = datetime.now(tz=self.tz)
        return today - timedelta(days=days)
