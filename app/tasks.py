import logging

from flask_apscheduler import APScheduler

from app.models import Wallet, db
from app.services.calculation_service import CalculationService

logger = logging.getLogger(__name__)
scheduler = APScheduler()


@scheduler.task("interval", id="update_wallets", minutes=10)
def update_wallets_job():
    with scheduler.app.app_context():
        calc_service = CalculationService()
        wallets = Wallet.query.all()
        for wallet in wallets:
            count = calc_service.update_wallet(wallet, db)
            logger.info(f"Carteira {wallet.address} atualizada: {count} transações novas!")
