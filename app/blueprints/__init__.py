from flask import Flask

from .txs import txs_bp
from .wallet import wallet_bp


def init_app(app: Flask):
    app.register_blueprint(wallet_bp)
    app.register_blueprint(txs_bp)
