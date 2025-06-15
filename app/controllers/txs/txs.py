from collections.abc import Sequence

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

from app.data.models import Transaction


class TxsController:
    def __init__(self, db: SQLAlchemy) -> None:
        self.db = db
        self.n_per_page = 20

    def get_txs(self, address: str, page: int) -> Sequence[Transaction]:
        offset = (page - 1) * self.n_per_page
        return self.db.session.scalars(
            select(Transaction)
            .filter_by(wallet_address=address)
            .order_by(Transaction.transaction_date.desc())
            .offset(offset)
            .limit(self.n_per_page)
        ).all()
