from flask import Blueprint, jsonify
from app import db
from app.models import Wallet, Transaction
from app.services.calculation_service import CalculationService

bp = Blueprint("wallet", __name__)


@bp.route("/<string:address>", methods=["GET"])
def get_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if not wallet:
        return jsonify({"error": "Carteira não encontrada"}), 404

    transactions = [
        {
            "transaction_id": tx.transaction_id,
            "transaction_date": tx.transaction_date.strftime("%d/%m/%Y"),
            "balance_btc": tx.balance_btc,
            "balance_usd": tx.balance_usd,
            "in": tx.tx_in,
        }
        for tx in wallet.transactions
    ]

    data = {
        "address": wallet.address,
        "balance_btc": wallet.balance_btc,
        "balance_usd": wallet.balance_usd,
        "transaction_count": wallet.transaction_count,
        "roa": wallet.roa,
        "first_transaction_date": wallet.first_transaction_date.strftime("%d/%m/%Y")
        if wallet.first_transaction_date
        else "Sem registro",
        "transactions": transactions,
    }
    return jsonify(data), 200


@bp.route("/<string:address>", methods=["POST"])
def add_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if wallet:
        return jsonify({"error": "Carteira já cadastrada."}), 400

    calc_service = CalculationService()
    wallet_data, tx_list = calc_service.calculate_wallet_data(address)
    if wallet_data is None:
        return jsonify({"error": "Falha ao obter dados da carteira."}), 500

    wallet = Wallet(
        address=address,
        balance_btc=wallet_data["balance_btc"],
        balance_usd=wallet_data["balance_usd"],
        transaction_count=wallet_data["transaction_count"],
        roa=wallet_data["roa"],
        first_transaction_date=wallet_data["first_transaction_date"],
    )
    db.session.add(wallet)

    for tx in tx_list:
        transaction = Transaction(
            transaction_id=tx["txid"],
            wallet_address=address,
            transaction_date=tx["transaction_date"],
            balance_btc=tx["balance_btc"],
            balance_usd=tx["balance_usd"],
            tx_in=tx["tx_in"],
        )
        db.session.add(transaction)

    db.session.commit()
    return jsonify({"message": "Carteira inserida e dados calculados."}), 201


@bp.route("/<string:address>", methods=["DELETE"])
def delete_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if not wallet:
        return jsonify({"error": "Carteira não encontrada."}), 404

    db.session.delete(wallet)
    db.session.commit()
    return jsonify({"message": f"Carteira {address} removida."}), 200
