import logging

from flask import Blueprint, jsonify

from app.models import Wallet, db
from app.schemas import WalletSchema
from app.services.calculation_service import CalculationService

bp = Blueprint("wallet", __name__)
logger = logging.getLogger(__name__)


@bp.get("/<string:address>")
def get_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if not wallet:
        return jsonify({"error": "Carteira não encontrada"}), 404
    wallet_data = WalletSchema().dump(wallet)
    return wallet_data, 200


@bp.post("/<string:address>")
def add_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if wallet:
        return jsonify({"error": "Carteira já cadastrada."}), 400

    calc_service = CalculationService()
    wallet_data, tx_list = calc_service.calculate_wallet_data(address)

    if wallet_data is None:
        return jsonify({"error": "Falha ao obter dados da carteira."}), 500

    try:
        wallet = calc_service.wallet_schema.load(wallet_data, session=db.session)
        transactions = (calc_service.tx_schema.load(tx, session=db.session) for tx in tx_list)
        db.session.add(wallet)
        db.session.add_all(transactions)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Falha ao inserir carteira no banco de dados: {e}")
        return jsonify({"error": "Falha ao adicionar a carteira"}), 500

    return jsonify({"message": "Carteira inserida e dados calculados."}), 201


@bp.delete("/<string:address>")
def delete_wallet(address):
    wallet = Wallet.query.filter_by(address=address).first()
    if not wallet:
        return jsonify({"error": "Carteira não encontrada."}), 404

    db.session.delete(wallet)
    db.session.commit()
    return jsonify({"message": f"Carteira {address} removida."}), 200
