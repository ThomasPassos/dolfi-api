from flask import Blueprint, jsonify

from app.models import Wallet, db
from app.schemas import WalletSchema
from app.services.calculation_service import CalculationService

bp = Blueprint("wallet", __name__)


@bp.route("/<string:address>", methods=["GET"])
def get_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if not wallet:
        return jsonify({"error": "Carteira não encontrada"}), 404
    wallet_data = WalletSchema().dump(wallet)
    return wallet_data, 200


@bp.route("/<string:address>", methods=["POST"])
def add_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if wallet:
        return jsonify({"error": "Carteira já cadastrada."}), 400

    calc_service = CalculationService()
    wallet_data, tx_list = calc_service.calculate_wallet_data(address)

    if wallet_data is None:
        return jsonify({"error": "Falha ao obter dados da carteira."}), 500

    wallet = calc_service.wallet_schema.load(wallet_data, session=db.session)
    for tx in tx_list:
        calc_service.tx_schema.load(tx, session=db.session)

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
