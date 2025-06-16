from datetime import datetime, timedelta

import pytz
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

from app.data.models import Transaction, Wallet
from app.data.schemas import WalletSchema
from app.data.wallet import WalletGenerator


class WalletTemporalController:
    def __init__(self, db: SQLAlchemy) -> None:
        self.db = db
        self.tz = pytz.timezone("America/Sao_Paulo")
        self.wallet_gen = WalletGenerator()
        self.schema = WalletSchema()

    def find_wallet(self, address: str) -> Wallet | None:
        return self.db.session.get(Wallet, address)

    def generate_temporal_wallet(self, wallet: Wallet, days: int) -> Wallet:
        date = self.calculate_date(days)
        txs = self.db.session.scalars(
            select(Transaction).where(Transaction.transaction_date >= date)
        ).all()
        txs_count = len(txs)
        invested, returned = self.wallet_gen.calculate_invested_and_returned(
            txs
        )
        roa = self.wallet_gen.calc.calculate_roa(
            invested,
            wallet.balance_usd,  # type: ignore
            returned,
        )
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
