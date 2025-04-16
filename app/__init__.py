import logging
import os

from dotenv import load_dotenv
from flask import Flask
from flask_talisman import Talisman
from loguru import logger

load_dotenv()


def create_app(config_object=None):
    try:
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_recycle": 3600,
        }
        app.config["SCHEDULER_API_ENABLED"] = True
        app.config["APSCHEDULER_JOB_DEFAULTS"] = {"coalesce": True, "max_instances": 1}

        if config_object:
            app.config.from_object(config_object)

        from app.ext.logging import InterceptHandler

        app.logger.handlers = [InterceptHandler()]
        app.logger.setLevel(logging.INFO)

        from app.ext.models import db

        db.init_app(app)

        from app.ext.schemas import ma

        ma.init_app(app)

        from app.ext.tasks import scheduler

        scheduler.init_app(app)

        # from app.ext.tasks import update_wallets_job  # noqa: F401

        scheduler.start()

        from app.routes import bp as wallet_bp

        app.register_blueprint(wallet_bp)

        # Talisman(app)
        with app.app_context():
            db.create_all()

        return app
    except Exception as e:
        logger.critical(f"Factory não retornando a aplicação: {e}")
        return None
