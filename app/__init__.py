import logging
import os
import traceback

from dotenv import load_dotenv
from flask import Flask
from flask_talisman import Talisman
from loguru import logger
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config


def create_app(config_object=Config):
    load_dotenv()

    try:
        app = Flask(__name__)
        if config_object:
            app.config.from_object(config_object)

        from app.ext.logging import InterceptHandler

        app.logger.handlers = [InterceptHandler()]
        if not app.debug:
            app.logger.setLevel(logging.INFO)

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
        # Inicialização das extensões
        from app.ext.models import db

        db.init_app(app)

        from app.ext.cache import cache

        cache.init_app(app)

        from app.ext.schemas import ma

        ma.init_app(app)

        from app.ext.tasks import scheduler, update_wallets_job

        scheduler.init_app(app)

        from app.ext.tasks import update_wallets_job
        # Iniciar o scheduler apenas em ambiente controlado
        if not app.debug and os.getenv("SCHEDULER_ENABLED"):
            scheduler.start()

        # Registro de blueprints
        from app.routes import bp as wallet_bp

        app.register_blueprint(wallet_bp)

        Talisman(app, force_https=False, content_security_policy=None)
        return app
    except Exception as e:
        logger.critical(f"Factory não retornando a aplicação: {e}\n{traceback.format_exc()}")
        return None
