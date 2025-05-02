from flask import Blueprint, current_app, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.external.cache import cache
from app.external.models import Transaction, db
from app.external.schemas import TransactionSchema
from app.services.auth import require_api_key

txs_bp = Blueprint("transaction", __name__)


@txs_bp.route("/txs/<string:address>/<int:page>", methods=["GET"])
@require_api_key
@cache.memoize(timeout=600)
def get_txs(address: str, page: int):
    current_app.logger.debug(f"Pegando as txs da carteira: {address}, página {page}")
    N_PER_PAGE = 20
    offset = (page - 1) * N_PER_PAGE
    try:
        txs = db.session.scalars(select(Transaction).filter_by(wallet_address=address).offset(offset).limit(N_PER_PAGE)).all()
    except SQLAlchemyError as e:
        current_app.logger.error(f"Erro ao pegar as txs da wallet {address}:\n{e}")
        return jsonify({"message": "Falha ao retornar as transações"}), 500
    if not txs:
        current_app.logger.warning(f"Não há txs para a wallet: {address}")
        return jsonify({"error": "Transações não encontradas"}), 404
    txs_data = TransactionSchema(many=True).dump(txs)
    current_app.logger.debug(f"Txs do {address} retornadas: {len(txs_data)} transações")
    return jsonify({"txs": txs_data}), 200


@txs_bp.route("/last_txs", methods=["GET"])
@require_api_key
@cache.memoize(timeout=600)
def get_last_txs():
    current_app.logger.debug("Retornando as 10 últimas txs")
    try:
        txs = db.session.scalars(select(Transaction).order_by(Transaction.transaction_date.desc()).limit(10)).all()
        response = TransactionSchema(many=True, only=("wallet_address", "transaction_date", "balance_usd")).jsonify(txs)
        current_app.logger.debug("10 últimas transações retornadas com sucesso")
        return response, 200
    except Exception as e:
        current_app.logger.error(f"Falha ao retornar as últimas txs: {e}")
        return {"message": "Falha ao retornar as transações"}, 500
