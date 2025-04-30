from flask_marshmallow import Marshmallow
from marshmallow import fields, post_dump
from marshmallow_sqlalchemy.fields import Nested

from app.external.models import Transaction, Wallet

ma = Marshmallow()


class TransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Transaction
        include_fk = True
        load_instance = True

    transaction_date = fields.DateTime(format="timestamp")

    @staticmethod
    def change_decimal_dump(data):
        data["balance_btc"] = float(data["balance_btc"])
        data["balance_usd"] = float(data["balance_usd"])
        return data

    @post_dump
    def format_json(self, data, many, **kwargs):
        data = self.change_decimal_dump(data)
        data["transaction_date"] = int(data["transaction_date"])
        return data


class WalletSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Wallet
        include_relationships = True
        load_instance = True

    first_transaction_date = fields.DateTime(format="timestamp")
    transactions = Nested(TransactionSchema, many=True, exclude=("wallet_address",))

    @staticmethod
    def change_decimal_dump(data):
        data["balance_btc"] = float(data["balance_btc"])
        data["balance_usd"] = float(data["balance_usd"])
        data["roa"] = float(data["roa"])
        if data.get("bitcoin_price_change"):
            data["btc_price_change"] = float(data["btc_price_change"])
        return data

    @post_dump
    def format_json(self, data, many, **kwargs):
        data = self.change_decimal_dump(data)
        data["first_transaction_date"] = int(data["first_transaction_date"])
        return data
