from collections.abc import Sequence
from typing import Any, Literal

from flask import current_app, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError

from app.controllers.wallets.all_wallets import AllWalletsController
from app.controllers.wallets.wallet import WalletController
from app.data.auth import header, require_api_key
from app.data.models import Wallet, db
from app.data.schemas import WalletSchema
from app.external.extensions.cache import cache

bp = Blueprint(
    "wallet",
    __name__,
    url_prefix="/wallets",
    description="Endpoint das Carteiras",
)


@bp.route("/all")
class AllWallets(MethodView):
    def __init__(self) -> None:
        self.controller = AllWalletsController(db)

    @bp.response(
        200,
        WalletSchema(
            many=True,
            exclude=(
                "transactions",
                "btc_price_change",
                "first_transaction_date",
                "transaction_count",
            ),
        ),
        description="Retorna todas as wallets",
        headers=header,
    )
    @require_api_key
    @cache.memoize(timeout=600)
    def get(self) -> Sequence[Wallet]:  # noqa: PLR6301
        """Pegar todas wallets

        Retorna todas as wallets registradas no banco de dados."""
        current_app.logger.debug("Pegando todas as wallets")
        wallets = self.controller.get_all_wallets()
        if not wallets:
            current_app.logger.warning("Não existem wallets salvas")
            abort(404, message="Carteiras não encontradas")
        current_app.logger.debug("Retornados os dados de todas as carteiras")
        return wallets


@bp.route("/<string:address>")
class Wallets(MethodView):
    def __init__(self) -> None:
        self.controller = WalletController(db)

    @bp.response(
        200,
        WalletSchema(exclude=("transactions",)),
        description="Retorna uma wallet",
        headers=header,
    )
    @require_api_key
    @cache.memoize(timeout=600)
    def get(self, address: str) -> Wallet:  # noqa: PLR6301
        """Pegar wallet

        Retorna a wallet que possui o endereço passado na URL."""
        current_app.logger.debug(f"Pegando os dados da wallet: {address}")
        wallet = self.controller.find_wallet(address)
        if not wallet:
            current_app.logger.warning(
                f"Requisição de wallet não existente: {address}"
            )
            abort(404, message="Carteira não encontrada")
        current_app.logger.debug(f"Dados entregues da wallet {address}")
        return wallet

    @bp.response(
        201,
        description="Carteira criada com sucesso",
        example={"message": "Carteira inserida e dados calculados."},
        headers=header,
    )
    def post(self, address: str) -> tuple[Any, Literal[201]]:  # noqa: PLR6301
        """Adicionar wallet

        Adiciona uma nova wallet e suas transações ao banco de dados."""
        current_app.logger.info(f"Adição da carteira {address} iniciada!")

        wallet = self.controller.find_wallet(address)
        if wallet:
            current_app.logger.warning(f"Carteira {address} já existe!")
            abort(400, message="Carteira já cadastrada")

        controller = WalletController(db)
        try:
            controller.insert_wallet_and_txs(address)
        except SQLAlchemyError as e:
            current_app.logger.error(
                f"Falha ao inserir carteira {address} no banco de dados:\n{e}"
            )
            db.session.rollback()
            abort(500, message="Falha ao adicionar a carteira")

        current_app.logger.info(
            f"Carteira {address} e transações adicionadas com sucesso!"
        )
        return jsonify({
            "message": "Carteira inserida e dados calculados."
        }), 201

    @bp.response(
        200,
        description="Carteira excluída com sucesso",
        example={"message": "Carteira {address} removida."},
        headers=header,
    )
    def delete(self, address: str) -> tuple[Any, Literal[200]]:  # noqa: PLR6301
        """Excluir wallet

        Exclui uma wallet e suas transações do banco de dados."""
        current_app.logger.info(f"Exclusão de carteira {address} iniciada!")
        wallet = self.controller.find_wallet(address)
        if not wallet:
            current_app.logger.warning(
                f"Carteira {address} não encontrada para exclusão!"
            )
            abort(404, message="Carteira não encontrada.")
        try:
            self.controller.delete_wallet(wallet)
            current_app.logger.info(f"Carteira {address} excluída!")
            return jsonify({"message": f"Carteira {address} removida."}), 200
        except SQLAlchemyError as e:
            current_app.logger.error(
                f"Erro ao deletar carteira {address}:\n{e}"
            )
            db.session.rollback()
            abort(500, message="Erro ao deletar a carteira.")
