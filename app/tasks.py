import logging
from datetime import datetime

from app import create_app, db
from app.models import Transaction, Wallet
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
                logger.error(f"Wallet info não encontrada para {wallet.address}")
                continue

            new_tx_count = wallet_info["chain_stats"]["tx_count"]
            has_new = new_tx_count > wallet.transaction_count

            if has_new:
                new_txs_generator = calc_service.update_wallet(wallet)
                for tx_data in new_txs_generator:
                    tx = Transaction(
                        transaction_id=tx_data["txid"],
                        wallet_address=wallet.address,
                        transaction_date=tx_data["transaction_date"],
                        balance_btc=tx_data["balance_btc"],
                        balance_usd=tx_data["balance_usd"],
                        tx_in=tx_data["tx_in"],
                    )
                    db.session.add(tx)
            else:
                current_price = calc_service.prices.get_bitcoin_price(datetime.now())
                wallet.balance_usd = wallet.balance_btc * current_price

                # Recalcula ROA com base nos dados atuais (sem refetchar todas as transações)
                (
                    _,
                    _processed_txs_listed_only_for_roa_calc_needed_here_if_not_stored_elsewhere_,
                ) = calc_service.calculate_wallet_data(wallet.address)
                (
                    _,
                    _processed_txs_listed_only_for_roa_calc_needed_here_if_not_stored_elsewhere_,
                ) = calc_service.calculate_wallet_data(wallet.address)

            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"Erro ao atualizar carteira {wallet.address}: {e}")
                db.session.rollback()
