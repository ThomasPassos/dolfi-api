from flask import Blueprint, current_app, jsonify

from app.ext.models import Wallet, db
from app.ext.schemas import WalletSchema
from app.services.calculation_service import CalculationService
from app.services.utils import require_api_key

bp = Blueprint("wallet", __name__)


@bp.route("/<string:address>", methods=["GET"])
@require_api_key
def get_wallet(address: str):
    current_app.logger.debug(f"Aquisição de dados da carteira: {address}")
    wallet = Wallet.query.filter_by(address=address).first()
    if not wallet:
        current_app.logger.warning(f"Requisição de carteira não existente: {address}")
        return jsonify({"error": "Carteira não encontrada"}), 404
    wallet_data = WalletSchema().dump(wallet)
    log_str = f"Dados entregues da wallet {address}: {wallet_data}!"
    current_app.logger.debug(log_str, extra=wallet_data)
    return wallet_data, 200


@bp.route("/<string:address>", methods=["POST"])
@require_api_key
def add_wallet(address: str):
    current_app.logger.info(f"Adição da carteira {address} iniciada!")
    wallet = Wallet.query.filter_by(address=address).first()
    if wallet:
        current_app.logger.warning(f"Carteira {address} já existe!")
        return jsonify({"error": "Carteira já cadastrada."}), 400

    calc_service = CalculationService()
    wallet_data, tx_list = calc_service.calculate_wallet_data(address)

    if wallet_data is None:
        current_app.logger.warning(f"Carteira {address} já existe!")
        return jsonify({"error": "Falha ao obter dados da carteira."}), 500

    wallet = calc_service.wallet_schema.load(wallet_data, session=db.session)
    if tx_list:
        transactions = (calc_service.tx_schema.load(tx, session=db.session) for tx in tx_list)
    try:
        db.session.add(wallet)
        db.session.add_all(transactions)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Falha ao inserir carteira {address} no banco de dados:\n {e}")
        db.session.rollback()
        return jsonify({"error": "Falha ao adicionar a carteira"}), 500

    current_app.logger.info(f"Wallet {address} e txs adicionada com sucesso!")
    return jsonify({"message": "Carteira inserida e dados calculados."}), 201


@bp.route("/<string:address>", methods=["DELETE"])
@require_api_key
def delete_wallet(address: str):
    current_app.logger.info(f"Exclusão de carteira {address} iniciada!")
    wallet = Wallet.query.filter_by(address=address).first()
    if not wallet:
        current_app.logger.info(f"Exclusão de carteira {address} iniciada!")
        return jsonify({"error": "Carteira não encontrada."}), 404
    try:
        db.session.delete(wallet)
        db.session.commit()
        current_app.logger.info(f"Carteira {address} excluída!")
        return jsonify({"message": f"Carteira {address} removida."}), 200
    except Exception as e:
        current_app.logger.error(f"Erro ao deletar carteira {address}:\n{e}")
        return jsonify({"message": "erro ao deletar carteira"}), 500
