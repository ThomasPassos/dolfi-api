from collections.abc import Sequence

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

from app.data.models import Wallet


class AllWalletsCtroller:
    def __init__(self, db: SQLAlchemy) -> None:
        self.db = db

    def get_all_wallets(self) -> Sequence[Wallet]:
        return self.db.session.scalars(select(Wallet)).all()
