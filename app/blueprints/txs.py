from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.external.cache import cache
from app.external.models import Transaction, db
from app.external.schemas import TransactionSchema
from app.services.auth import header, require_api_key

bp = Blueprint(
    "transaction",
    __name__,
    url_prefix="/txs",
    description="Endpoint das Transações",
)


@bp.route("/<string:address>/<page:int>")
class Txs(MethodView):
    @bp.response(
        200,
        TransactionSchema(many=True),
        headers=header,
        description="""Retorna as transações de uma wallet específica,
        cada página possui 20 transações""",
    )
    @require_api_key
    @cache.memoize(timeout=600)
    def get(self, address: str, page: int):  # noqa: PLR6301
        """Pegar transações

        Retorna 20 transações de uma wallet específica"""
        current_app.logger.debug(
            f"Pegando as txs da carteira: {address}, página {page}"
        )
        N_PER_PAGE = 20
        offset = (page - 1) * N_PER_PAGE
        try:
            txs = db.session.scalars(
                select(Transaction)
                .filter_by(wallet_address=address)
                .order_by(Transaction.transaction_date.desc())
                .offset(offset)
                .limit(N_PER_PAGE)
            ).all()
        except SQLAlchemyError as e:
            current_app.logger.error(
                f"Erro ao pegar as txs da wallet {address}:\n{e}"
            )
            abort(500, message="Erro ao pegar as txs")
        if not txs:
            current_app.logger.warning(f"Não há txs para a wallet: {address}")
            abort(404, message="Transações não encontradas")
        current_app.logger.debug(
            f"Txs do {address} retornadas: {len(txs)} transações"
        )
        return txs


@bp.route("/last_txs")
class LastTxs(MethodView):
    @bp.response(
        200,
        TransactionSchema(
            many=True,
            only=("wallet_address", "transaction_date", "balance_usd"),
        ),
        headers=header,
        description="""Retorna as 10 transações mais recentes
        presentes na base de dados""",
    )
    @require_api_key
    @cache.memoize(timeout=600)
    def get(self):  # noqa: PLR6301
        """Pegar últimas transações

        Retorna as 10 últimas transações da base de dados."""
        current_app.logger.debug("Retornando as 10 últimas txs")
        try:
            txs = db.session.scalars(
                select(Transaction)
                .order_by(Transaction.transaction_date.desc())
                .limit(10)
            ).all()
            current_app.logger.debug(
                "10 últimas transações retornadas com sucesso"
            )
            return txs
        except Exception as e:
            current_app.logger.error(f"Falha ao retornar as últimas txs: {e}")
            abort(500, message="Falha ao retornar as transações")
