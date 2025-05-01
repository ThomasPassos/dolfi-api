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
def get_transactions(address: str, page: int):
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
    return jsonify({"txs": txs_data}), 200
