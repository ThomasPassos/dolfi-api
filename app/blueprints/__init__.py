from flask import Flask
from flask_smorest import Api

from .txs import bp as txs_bp
from .wallet import bp as wallet_bp

api = Api()


def init_app(app: Flask) -> Flask:
    api.init_app(app)
    api.register_blueprint(wallet_bp)
    api.register_blueprint(txs_bp)
    return app
