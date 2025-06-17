from decimal import Decimal
from typing import Any

from flask_marshmallow import Marshmallow
from marshmallow import fields, post_dump
from marshmallow_sqlalchemy.fields import Nested

from app.data.models import Transaction, Wallet

ma = Marshmallow()


class TransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Transaction
        include_fk = True
        load_instance = True

    transaction_date = fields.DateTime(format="timestamp")

    @staticmethod
    def decimal_to_float(data: dict[str, Any]) -> dict[str, Any]:
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data

    @post_dump
    def format_json(
        self,
        data: dict[str, Any],
        *args: tuple,  # noqa: ARG002
        **kwargs: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, Any]:
        data = self.decimal_to_float(data)
        data["transaction_date"] = int(data["transaction_date"])
        return data


class WalletSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Wallet
        include_relationships = True
        load_instance = True

    first_transaction_date = fields.DateTime(format="timestamp")
    transactions = Nested(
        TransactionSchema, many=True, exclude=("wallet_address",)
    )

    @staticmethod
    def decimal_to_float(data: dict[str, Any]) -> dict[str, Any]:
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data

    @post_dump
    def format_json(
        self,
        data: dict[str, Any],
        *args: tuple,  # noqa: ARG002
        **kwargs: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, Any]:
        data = self.decimal_to_float(data)
        if data.get("first_transaction_date"):
            data["first_transaction_date"] = int(
                data["first_transaction_date"]
            )
        return data
