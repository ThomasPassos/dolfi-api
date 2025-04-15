from datetime import datetime

from flask_marshmallow import Marshmallow
from marshmallow import fields, post_dump
from marshmallow_sqlalchemy.fields import Nested

from app.models import Transaction, Wallet

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
        date = datetime.strptime(data["first_transaction_date"], "%Y-%m-%dT%H:%M:%S")
        data["first_transaction_date"] = date.strftime("%d/%m/%Y, %H:%M:%S")
        return data
