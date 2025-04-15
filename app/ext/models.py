from datetime import datetime
from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


class Wallet(db.Model):
    __tablename__ = "wallet"
    address: Mapped[str] = mapped_column(primary_key=True)
    balance_btc: Mapped[float] = mapped_column(default=0)
    balance_usd: Mapped[float] = mapped_column(default=0)
    transaction_count: Mapped[int] = mapped_column(default=0)
    roa: Mapped[float] = mapped_column(default=0)
    # btc_val: Mapped[float] = mapped_column(default=0)
    first_transaction_date: Mapped[Optional[datetime]] = mapped_column()
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="wallet", cascade="all, delete-orphan"
    )


class Transaction(db.Model):
    __tablename__ = "transaction"
    transaction_id: Mapped[str] = mapped_column(primary_key=True)
    wallet_address: Mapped[str] = mapped_column(
        db.ForeignKey("wallet.address"), nullable=False, index=True
    )
    transaction_date: Mapped[datetime] = mapped_column(nullable=False)
    balance_btc: Mapped[float] = mapped_column(default=0)
    balance_usd: Mapped[float] = mapped_column(default=0)
    tx_in: Mapped[bool] = mapped_column(default=True)
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="transactions")
