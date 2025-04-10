import logging

from app import create_app
from app.models import Wallet
from app.services.calculation_service import CalculationService

logger = logging.getLogger(__name__)


def update_wallets_job():
    app = create_app()
    with app.app_context():
        calc_service = CalculationService()
        wallets = Wallet.query.all()
        for wallet in wallets:
            wallet_info = calc_service.blockchain.get_wallet_info(wallet.address)
            if not wallet_info:
                logger.error(f"Informações da Wallet não encontradas para {wallet.address}")
                continue
