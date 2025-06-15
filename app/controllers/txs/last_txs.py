from collections.abc import Sequence

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

from app.data.models import Transaction


class LastTxsController:
    def __init__(self, db: SQLAlchemy) -> None:
        self.db = db

    def get_last_txs(self) -> Sequence[Transaction]:
        return self.db.session.scalars(
            select(Transaction)
            .order_by(Transaction.transaction_date.desc())
            .limit(10)
        ).all()
