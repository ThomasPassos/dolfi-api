from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class Wallet(db.Model):
    __tablename__ = "wallet"
    address: Mapped[str] = mapped_column(primary_key=True)
    balance_btc: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0)
    balance_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    transaction_count: Mapped[int] = mapped_column(default=0)
    roa: Mapped[Decimal] = mapped_column(default=0)
    btc_price_change: Mapped[Decimal] = mapped_column(default=0)
    first_transaction_date: Mapped[Optional[datetime]] = mapped_column()
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")


class Transaction(db.Model):
    __tablename__ = "transaction"
    transaction_id: Mapped[str] = mapped_column(primary_key=True)
    wallet_address: Mapped[str] = mapped_column(db.ForeignKey("wallet.address"), nullable=False, index=True)
    transaction_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    balance_btc: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0)
    balance_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    is_incoming: Mapped[bool] = mapped_column(default=True)
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="transactions")
