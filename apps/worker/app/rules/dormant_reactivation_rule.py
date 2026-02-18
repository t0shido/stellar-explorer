"""
Rule 3: Dormant account reactivation (no activity > X days, then large tx)
"""
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from decimal import Decimal

from app.rules.base import BaseRule, RuleResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class DormantReactivationRule(BaseRule):
    """Detect dormant accounts that suddenly become active with large transactions"""
    
    def is_enabled(self) -> bool:
        return settings.RULE_DORMANT_REACTIVATION_ENABLED
    
    def evaluate(self, db: Session) -> List[RuleResult]:
        """
        Check for dormant account reactivation
        
        Logic:
        1. Get all watched accounts
        2. Check if account was dormant (no activity > X days)
        3. Check for recent large transactions
        """
        if not self.is_enabled():
            return []
        
        from app.db.models import (
            WatchlistMember, Account, Operation, Transaction, Asset
        )
        
        results = []
        dormant_days = settings.RULE_DORMANT_DAYS_THRESHOLD
        amount_threshold = Decimal(str(settings.RULE_DORMANT_AMOUNT_THRESHOLD))
        
        # Get all watched accounts
        watched_accounts = db.query(Account).join(
            WatchlistMember,
            Account.id == WatchlistMember.account_id
        ).distinct().all()
        
        logger.info(
            f"Evaluating dormant reactivation rule",
            extra={
                "watched_accounts": len(watched_accounts),
                "dormant_days": dormant_days,
                "amount_threshold": float(amount_threshold)
            }
        )
        
        # Define time windows
        dormant_cutoff = datetime.utcnow() - timedelta(days=dormant_days)
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        
        for account in watched_accounts:
            # Check if account has last_seen older than dormant threshold
            if not account.last_seen or account.last_seen > dormant_cutoff:
                continue  # Not dormant
            
            # Check for recent activity (last hour)
            recent_ops = db.query(Operation, Transaction, Asset).join(
                Transaction,
                Operation.tx_id == Transaction.id
            ).outerjoin(
                Asset,
                Operation.asset_id == Asset.id
            ).filter(
                and_(
                    Operation.from_account_id == account.id,
                    Operation.amount >= amount_threshold,
                    Operation.created_at >= recent_cutoff,
                    Transaction.successful == True
                )
            ).all()
            
            if recent_ops:
                # Account was dormant and now has large transactions
                for operation, transaction, asset in recent_ops:
                    # Calculate dormancy period
                    dormant_days_actual = (operation.created_at - account.last_seen).days if account.last_seen else None
                    
                    result = RuleResult(
                        rule_name="dormant_reactivation",
                        fired=True,
                        severity=settings.RULE_DORMANT_REACTIVATION_SEVERITY,
                        account_id=account.id,
                        asset_id=asset.id if asset else None,
                        evidence={
                            "account_address": account.address,
                            "dormant_days_threshold": dormant_days,
                            "dormant_days_actual": dormant_days_actual,
                            "last_activity": account.last_seen.isoformat() if account.last_seen else None,
                            "reactivation_time": operation.created_at.isoformat(),
                            "amount": str(operation.amount),
                            "amount_threshold": str(amount_threshold),
                            "asset_code": asset.asset_code if asset else "XLM",
                            "asset_issuer": asset.asset_issuer if asset else None,
                            "transaction_hash": transaction.tx_hash,
                            "ledger": transaction.ledger,
                            "operation_type": operation.type
                        },
                        message=f"Dormant account {account.address} reactivated after {dormant_days_actual} days with large transaction of {operation.amount} {asset.asset_code if asset else 'XLM'}"
                    )
                    results.append(result)
                    
                    logger.warning(
                        f"Dormant account reactivation detected",
                        extra={
                            "account": account.address,
                            "dormant_days": dormant_days_actual,
                            "amount": str(operation.amount)
                        }
                    )
        
        self.log_evaluation(results)
        return results
