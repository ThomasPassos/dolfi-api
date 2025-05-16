from flask import current_app, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.external.cache import cache
from app.external.models import Wallet, db
from app.external.schemas import WalletSchema
from app.services.auth import header, require_api_key
from app.services.calculation_service import DolfiCalculator

bp = Blueprint(
    "wallet",
    __name__,
    url_prefix="/wallets",
    description="Endpoint das Carteiras",
)


@bp.route("/all")
class AllWallets(MethodView):
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
    @bp.alt_response(401, description="Erro de autenticação")
    @require_api_key
    @cache.memoize(timeout=600)
    def get(self):  # noqa: PLR6301
        """Pegar todas wallets

        Retorna todas as wallets registradas no banco de dados."""
        current_app.logger.debug("Pegando todas as wallets")
        wallets = db.session.scalars(select(Wallet)).all()
        if not wallets:
            current_app.logger.warning("Não existem wallets salvas")
            abort(404, message="Carteiras não encontradas")
        current_app.logger.debug("Retornados os dados de todas as carteiras")
        return wallets


@bp.route("/<string:address>")
class Wallets(MethodView):
    @bp.response(
        200,
        WalletSchema(exclude=("transactions",)),
        description="Retorna uma wallet",
        headers=header,
    )
    @require_api_key
    @cache.memoize(timeout=600)
    def get(self, address: str):  # noqa: PLR6301
        """Pegar wallet

        Retorna a wallet que possui o endereço passado na URL."""
        current_app.logger.debug(f"Pegando os dados da wallet: {address}")
        wallet = db.session.get(Wallet, address)
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
    def post(self, address: str):  # noqa: PLR6301
        """Adicionar wallet

        Adiciona uma nova wallet e suas transações ao banco de dados."""
        current_app.logger.info(f"Adição da carteira {address} iniciada!")
        wallet = db.session.get(Wallet, address)
        if wallet:
            current_app.logger.warning(f"Carteira {address} já existe!")
            abort(400, message="Carteira já cadastrada")

        calc_service = DolfiCalculator()
        wallet_data, tx_list = calc_service.calculate_wallet_data(address)

        if wallet_data is None:
            current_app.logger.warning(
                f"Falha ao obter dados da carteira {address}!"
            )
            abort(500, message="Falha ao obter dados da carteira.")

        wallet = calc_service.wallet_schema.load(
            wallet_data,
            session=db.session,  # type: ignore
        )
        transactions = []
        if tx_list:
            transactions = [
                calc_service.tx_schema.load(tx, session=db.session)  # type: ignore
                for tx in tx_list
            ]

        try:
            db.session.add(wallet)
            db.session.add_all(transactions)
            db.session.commit()
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
    def delete(self, address: str):  # noqa: PLR6301
        """Excluir wallet

        Exclui uma wallet e suas transações do banco de dados."""
        current_app.logger.info(f"Exclusão de carteira {address} iniciada!")
        wallet = db.session.get(Wallet, address)
        if not wallet:
            current_app.logger.warning(
                f"Carteira {address} não encontrada para exclusão!"
            )
            abort(404, message="Carteira não encontrada.")
        try:
            db.session.delete(wallet)
            db.session.commit()
            current_app.logger.info(f"Carteira {address} excluída!")
            return jsonify({"message": f"Carteira {address} removida."}), 200
        except SQLAlchemyError as e:
            current_app.logger.error(
                f"Erro ao deletar carteira {address}:\n{e}"
            )
            db.session.rollback()
            abort(500, message="Erro ao deletar a carteira.")
