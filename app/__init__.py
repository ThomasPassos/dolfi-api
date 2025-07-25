import logging

from dotenv import load_dotenv
from flask import Flask
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config


def create_app(config_object: object = Config) -> Flask:
    load_dotenv()

    app = Flask(__name__)
    if config_object:
        app.config.from_object(config_object)

    from app.external.extensions.logging import InterceptHandler

    app.logger.handlers = [InterceptHandler()]
    if not app.debug:
        app.logger.setLevel(logging.INFO)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
    )
    # Inicialização das extensões
    from app.data.models import db, migrate

    db.init_app(app)
    migrate.init_app(app, db)

    from app.external.extensions.cache import cache

    cache.init_app(app)

    from app.data.schemas import ma

    ma.init_app(app)

    # Inicialização do Celery
    import app.external.extensions.celery as cl

    cl.init_app(app)

    # Registro de blueprints
    import app.blueprints as bp

    bp.init_app(app)

    Talisman(app, force_https=False, content_security_policy=None)
    return app
