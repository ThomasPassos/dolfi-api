from flask import Blueprint, current_app, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.ext.models import Transaction, Wallet, db
from app.ext.schemas import TransactionSchema, WalletSchema
from app.services.auth import require_api_key
from app.services.calculation_service import CalculationService

bp = Blueprint("wallet", __name__)


@bp.route("/<string:address>", methods=["GET"])
@require_api_key
def get_wallet(address: str):
    current_app.logger.debug(f"Pegando os dados da wallet: {address}")
    wallet = db.session.get(Wallet, address)
    if not wallet:
        current_app.logger.warning(f"Requisição de wallet não existente: {address}")
        return jsonify({"error": "Carteira não encontrada"}), 404
    wallet_data = WalletSchema(exclude=("transactions",)).dump(wallet)
    current_app.logger.debug(f"Dados entregues da wallet {address}: {wallet_data}")
    return jsonify(wallet_data), 200


@bp.route("/txs/<string:address>/<int:page>", methods=["GET"])
@require_api_key
def get_transactions(address: str, page: int = 1):
    current_app.logger.debug(f"Pegando as txs da carteira: {address}, página {page}")
    N_PER_PAGE = 20
    offset = (page - 1) * N_PER_PAGE
    try:
        txs = (
            db.session.execute(select(Transaction).where(Transaction.wallet_address == address).offset(offset).limit(N_PER_PAGE))
            .scalars()
            .all()
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Erro ao pegar as txs da wallet {address}:\n{e}")
        return jsonify({"message": "Falha ao retornar as transações"}), 500
    if not txs:
        current_app.logger.warning(f"Não há txs para a wallet: {address}")
        return jsonify({"error": "Transações não encontradas"}), 404
    txs_data = TransactionSchema(many=True).dump(txs)
    current_app.logger.debug(f"Txs do {address} retornadas: {len(txs_data)} transações")
    return jsonify(txs_data), 200


@bp.route("/<string:address>", methods=["POST"])
@require_api_key
def add_wallet(address: str):
    current_app.logger.info(f"Adição da carteira {address} iniciada!")
    wallet = db.session.get(Wallet, address)
    if wallet:
        current_app.logger.warning(f"Carteira {address} já existe!")
        return jsonify({"error": "Carteira já cadastrada."}), 400

    calc_service = CalculationService()
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


@bp.route("/<string:address>", methods=["DELETE"])
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
