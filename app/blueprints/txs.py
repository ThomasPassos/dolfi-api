from collections.abc import Sequence

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError

from app.controllers.txs.last_txs import LastTxsController
from app.controllers.txs.txs import TxsController
from app.data.auth import header, require_api_key
from app.data.models import Transaction, db
from app.data.schemas import TransactionSchema
from app.external.extensions.cache import cache

bp = Blueprint(
    "transaction",
    __name__,
    url_prefix="/txs",
    description="Endpoint das Transações",
)


@bp.route("/<string:address>/<int:page>")
class Txs(MethodView):
    def __init__(self) -> None:
        self.controller = TxsController(db)

    @bp.response(
        200,
        TransactionSchema(many=True),
        headers=header,
        description="""Retorna as transações de uma wallet específica,
        cada página possui 20 transações""",
    )
    @require_api_key
    @cache.memoize(timeout=600)
    def get(self, address: str, page: int) -> Sequence[Transaction]:  # noqa: PLR6301
        """Pegar transações

        Retorna 20 transações de uma wallet específica"""
        current_app.logger.debug(
            f"Pegando as txs da carteira: {address}, página {page}"
        )
        try:
            txs = self.controller.get_txs(address, page)
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


@bp.route("/last")
class LastTxs(MethodView):
    def __init__(self) -> None:
        self.controller = LastTxsController(db)

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
    def get(self) -> Sequence[Transaction]:  # noqa: PLR6301
        """Pegar últimas transações

        Retorna as 10 últimas transações da base de dados."""
        current_app.logger.debug("Retornando as 10 últimas txs")
        try:
            txs = self.controller.get_last_txs()
            current_app.logger.debug(
                "10 últimas transações retornadas com sucesso"
            )
            return txs
        except Exception as e:
            current_app.logger.error(f"Falha ao retornar as últimas txs: {e}")
            abort(500, message="Falha ao retornar as transações")
