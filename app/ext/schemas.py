from datetime import datetime

from flask_marshmallow import Marshmallow
from marshmallow import fields, post_dump
from marshmallow_sqlalchemy.fields import Nested

from app.ext.models import Transaction, Wallet

ma = Marshmallow()


class TransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Transaction
        include_fk = True
        load_instance = True

    transaction_date = fields.DateTime()

    @post_dump
    @staticmethod
    def change_date_dump(data, many, *kwargs):
        date = datetime.strptime(data["transaction_date"], "%Y-%m-%dT%H:%M:%S")
        data["transaction_date"] = date.strftime("%d/%m/%Y, %H:%M:%S")
        return data

    @post_dump
    @staticmethod
    def change_decimal_dump(data, many, **kwargs):
        data["balance_btc"] = float(data["balance_btc"])
        data["balance_usd"] = float(data["balance_usd"])
        return data


class WalletSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Wallet
        include_relationships = True
        load_instance = True

    first_transaction_date = fields.DateTime()
    transactions = Nested(TransactionSchema, many=True, exclude=("wallet_address",))

    @post_dump
    @staticmethod
    def change_date_dump(data, many, **kwargs):
        if data.get("first_transaction_date"):
            date = datetime.strptime(data["first_transaction_date"], "%Y-%m-%dT%H:%M:%S")
            data["first_transaction_date"] = date.strftime("%d/%m/%Y, %H:%M:%S")
            return data
        return data

    @post_dump
    @staticmethod
    def change_decimal_dump(data, many, **kwargs):
        data["balance_btc"] = float(data["balance_btc"])
        data["balance_usd"] = float(data["balance_usd"])
        data["roa"] = float(data["roa"])
        if data.get("bitcoin_price_change"):
            data["btc_price_change"] = float(data["btc_price_change"])
        return data
