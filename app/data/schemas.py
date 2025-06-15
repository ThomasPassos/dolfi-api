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
    def change_decimal_dump(data: dict[str, Any]) -> dict[str, Any]:
        if data.get("balance_btc"):
            data["balance_btc"] = float(data["balance_btc"])
        if data.get("balance_usd"):
            data["balance_usd"] = float(data["balance_usd"])
        return data

    @post_dump
    def format_json(
        self,
        data: dict[str, Any],
        *args: tuple,  # noqa: ARG002
        **kwargs: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, Any]:
        data = self.change_decimal_dump(data)
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
    def change_decimal_dump(data: dict[str, Any]) -> dict[str, Any]:
        data["balance_btc"] = float(data["balance_btc"])
        data["balance_usd"] = float(data["balance_usd"])
        data["roa"] = float(data["roa"])
        if data.get("bitcoin_price_change"):
            data["btc_price_change"] = float(data["btc_price_change"])
        return data

    @post_dump
    def format_json(
        self,
        data: dict[str, Any],
        *args: tuple,  # noqa: ARG002
        **kwargs: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, Any]:
        data = self.change_decimal_dump(data)
        if data.get("first_transaction_date"):
            data["first_transaction_date"] = int(
                data["first_transaction_date"]
            )
        return data
