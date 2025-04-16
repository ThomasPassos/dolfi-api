from flask_apscheduler import APScheduler
from sqlalchemy import select

from app.ext.models import Wallet, db
from app.services.calculation_service import CalculationService

scheduler = APScheduler()


@scheduler.task("cron", id="update_wallets", hour=15, minute=0)
def update_wallets_job():
    with scheduler.app.app_context():
        scheduler.app.logger.info("Processo de atualização de dados iniciado")
        calc_service = CalculationService()
        wallets = db.session.execute(select(Wallet)).scalars().all()
        if wallets:
            for wallet in wallets:
                count = calc_service.update_wallet(wallet, db)
                log_str = f"Carteira {wallet.address} atualizada: {count} transações novas!"
                scheduler.app.logger.info(log_str)
        scheduler.app.logger.warning("Nenhuma carteira foi retornada da base de dados")
