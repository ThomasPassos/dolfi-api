from flask_apscheduler import APScheduler
from sqlalchemy import select

from app.external.models import Wallet, db
from app.services.calculation_service import DolfiCalculator

scheduler = APScheduler()


@scheduler.task("cron", id="update_wallets", hour=15, minute=0)
def update_wallets_job():
    with scheduler.app.app_context():
        scheduler.app.logger.info("Processo de atualização de dados iniciado")
        calc_service = DolfiCalculator()
        wallets = db.session.execute(select(Wallet)).scalars().all()
        try:
            if wallets:
                for wallet in wallets:
                    scheduler.app.logger.info(f"Atualizando carteira {wallet.address}!")
                    calc_service.update_wallet(wallet, db)
                    scheduler.app.logger.info(f"Carteira {wallet.address} atualizada!")
            else:
                scheduler.app.logger.warning("Nenhuma carteira foi retornada da base de dados")
        except Exception as e:
            scheduler.app.logger.error(f"Erro na tarefa de atualização: {e}")
