import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()


def create_app(config_object=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SCHEDULER_API_ENABLED"] = True
    app.config["APSCHEDULER_JOB_DEFAULTS"] = {"coalesce": True, "max_instances": 1}

    if config_object:
        app.config.from_object(config_object)

    from app.models import db  # noqa: PLC0415

    db.init_app(app)

    from app.tasks import scheduler  # noqa: PLC0415

    scheduler.init_app(app)

    from app.tasks import update_wallets_job  # noqa: F401, PLC0415

    scheduler.start()

    from app.routes import bp as wallet_bp  # noqa: PLC0415

    app.register_blueprint(wallet_bp)

    with app.app_context():
        db.create_all()

    return app
