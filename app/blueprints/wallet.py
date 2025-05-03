from flask import Blueprint, current_app, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.external.cache import cache
from app.external.models import Wallet, db
from app.external.schemas import WalletSchema
from app.external.tasks import update_all_wallets
from app.services.auth import require_api_key
from app.services.calculation_service import DolfiCalculator

wallet_bp = Blueprint("wallet", __name__)


@wallet_bp.route("/all", methods=["GET"])
@require_api_key
@cache.cached(timeout=600)
def get_all_wallet():
    current_app.logger.debug("Pegando todas as wallets")
    wallets = db.session.scalars(select(Wallet)).all()
    if not wallets:
        current_app.logger.warning("Não existem wallets salvas")
        return jsonify({"error": "Carteiras não encontradas"}), 404
    current_app.logger.debug("Retornados os dados de todas as carteiras")
    exclusion_group = ("transactions", "btc_price_change", "first_transaction_date", "transaction_count")
    response = WalletSchema(many=True, exclude=exclusion_group).jsonify(wallets)
    return response, 200


@wallet_bp.route("/<string:address>", methods=["GET"])
@require_api_key
@cache.memoize(timeout=600)
def get_wallet(address: str):
    current_app.logger.debug(f"Pegando os dados da wallet: {address}")
    wallet = db.session.get(Wallet, address)
    if not wallet:
        current_app.logger.warning(f"Requisição de wallet não existente: {address}")
        return jsonify({"error": "Carteira não encontrada"}), 404
    current_app.logger.debug(f"Dados entregues da wallet {address}")
    return WalletSchema(exclude=("transactions",)).jsonify(wallet), 200


@wallet_bp.route("/<string:address>", methods=["DELETE"])
@require_api_key
def delete_wallet(address: str):
    current_app.logger.info(f"Exclusão de carteira {address} iniciada!")
    wallet = db.session.get(Wallet, address)
    if not wallet:
        current_app.logger.warning(f"Carteira {address} não encontrada para exclusão!")
        return jsonify({"error": "Carteira não encontrada."}), 404
    try:
        db.session.delete(wallet)
        db.session.commit()
        current_app.logger.info(f"Carteira {address} excluída!")
        return jsonify({"message": f"Carteira {address} removida."}), 200
    except SQLAlchemyError as e:
        current_app.logger.error(f"Erro ao deletar carteira {address}:\n{e}")
        db.session.rollback()
        return jsonify({"message": "Erro ao deletar a carteira."}), 500


@wallet_bp.route("/<string:address>", methods=["POST"])
@require_api_key
def add_wallet(address: str):
    current_app.logger.info(f"Adição da carteira {address} iniciada!")
    wallet = db.session.get(Wallet, address)
    if wallet:
        current_app.logger.warning(f"Carteira {address} já existe!")
        return jsonify({"error": "Carteira já cadastrada."}), 400

    calc_service = DolfiCalculator()
    wallet_data, tx_list = calc_service.calculate_wallet_data(address)

    if wallet_data is None:
        current_app.logger.warning(f"Falha ao obter dados da carteira {address}!")
        return jsonify({"error": "Falha ao obter dados da carteira."}), 500

    wallet = calc_service.wallet_schema.load(wallet_data, session=db.session)
    transactions = []
    if tx_list:
        transactions = [calc_service.tx_schema.load(tx, session=db.session) for tx in tx_list]

    try:
        db.session.add(wallet)
        db.session.add_all(transactions)
        db.session.commit()
    except SQLAlchemyError as e:
        current_app.logger.error(f"Falha ao inserir carteira {address} no banco de dados:\n{e}")
        db.session.rollback()
        return jsonify({"error": "Falha ao adicionar a carteira"}), 500

    current_app.logger.info(f"Carteira {address} e transações adicionadas com sucesso!")
    return jsonify({"message": "Carteira inserida e dados calculados."}), 201
