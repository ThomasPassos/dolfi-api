import logging

from flask_apscheduler import APScheduler
from sqlalchemy import select
from app.ext.models import Wallet, db
from app.services.calculation_service import CalculationService

logger = logging.getLogger(__name__)
scheduler = APScheduler()


@scheduler.task("interval", id="update_wallets", minutes=10)
def update_wallets_job():
    with scheduler.app.app_context():
        calc_service = CalculationService()
        wallets = db.session.execute(select(Wallet)).scalars().all()
        for wallet in wallets:
            count = calc_service.update_wallet(wallet, db)
            logger.info(f"Carteira {wallet.address} atualizada: {count} transações novas!")
