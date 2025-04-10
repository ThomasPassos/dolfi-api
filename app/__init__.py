import os

from dotenv import load_dotenv
from flask import Flask
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy

from app.routes import bp as wallet_bp
from app.tasks import update_wallets_job

load_dotenv()
db = SQLAlchemy()
scheduler = APScheduler()


def create_app(config_object=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SCHEDULER_API_ENABLED"] = True
    app.config["APSCHEDULER_JOB_DEFAULTS"] = {"coalesce": True, "max_instances": 1}

    if config_object:
        app.config.from_object(config_object)

    db.init_app(app)
    scheduler.init_app(app)
    scheduler.start()

    app.register_blueprint(wallet_bp)

    scheduler.add_job(
        id="update_wallets", func=update_wallets_job, trigger="interval", minutes=10
    )

    with app.app_context():
        db.create_all()

    return app
