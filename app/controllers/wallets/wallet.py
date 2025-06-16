from flask_sqlalchemy import SQLAlchemy

from app.data.calculation import Calculator
from app.data.models import Wallet
from app.data.wallet import WalletGenerator


class WalletController:
    def __init__(self, db: SQLAlchemy) -> None:
        self.db = db
        self.calc = Calculator()
        self.wallet_gen = WalletGenerator()

    def find_wallet(self, address: str) -> Wallet | None:
        return self.db.session.get(Wallet, address)

    def delete_wallet(self, wallet: Wallet) -> None:
        self.db.session.delete(wallet)
        self.db.session.commit()

    def insert_wallet_and_txs(self, address: str) -> None:
        wallet, txs = self.wallet_gen.generate_wallet_and_txs(address)
        self.db.session.add(wallet)
        self.db.session.add_all(txs)
        self.db.session.commit()
