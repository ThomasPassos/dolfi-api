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

    @post_dump
    @staticmethod
    def format_json(
        data: dict[str, Any],
        *args: tuple,  # noqa: ARG004
        **kwargs: dict[str, Any],  # noqa: ARG004
    ) -> dict[str, Any]:
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

    @post_dump
    @staticmethod
    def format_json(
        data: dict[str, Any],
        *args: tuple,  # noqa: ARG004
        **kwargs: dict[str, Any],  # noqa: ARG004
    ) -> dict[str, Any]:
        if data.get("first_transaction_date"):
            data["first_transaction_date"] = int(
                data["first_transaction_date"]
            )
        return data
