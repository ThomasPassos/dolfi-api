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
            wallet_info = calc_service.blockchain.get_wallet_info(wallet.address)
            if not wallet_info:
                logger.error(f"Wallet info não encontrada para {wallet.address}")
                continue
            calc_service.update_wallet(wallet, db)
